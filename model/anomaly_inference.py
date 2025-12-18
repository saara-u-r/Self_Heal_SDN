# ============================================================
# anomaly_inference.py
# Runs LSTM + Isolation Forest inference and extracts reasons
# ============================================================

import numpy as np
import joblib
import tensorflow as tf


class AnomalyInference:

    def __init__(self):

        # -------------------------------
        # Load LSTM model + scaler
        # -------------------------------
        self.lstm_model = tf.keras.models.load_model(
            "lstmModels/lstm_best_model.h5",
            custom_objects={"r2_metric": lambda y_true, y_pred: 0}
        )
        self.lstm_scaler = joblib.load("lstmModels/lstm_scaler.pkl")
        self.lstm_info = joblib.load("lstmModels/lstm_threshold_info.pkl")
        self.lstm_threshold = self.lstm_info["threshold"]

        # Feature names (matching training)
        self.lstm_feature_names = [
            "CPU spike / overload",
            "Memory leak or sudden increase",
            "RTT spike / latency anomaly",
            "Packet-In burst / possible DoS",
            "Controller broadcast spike",
            "Flow churn anomaly",
            "Flow churn anomaly",
            "Bandwidth anomaly"
        ]

        self.seq_len = 20
        self.buffer = []

        # -------------------------------
        # Load Isolation Forest components
        # -------------------------------
        self.if_model = joblib.load("ifmodels/isolation_forest_model.pkl")
        self.if_scaler = joblib.load("ifmodels/if_scaler.pkl")
        self.if_threshold = joblib.load("ifmodels/if_threshold_info.pkl")["threshold"]

        # Pretty names from IF training script
        self.pretty = {
            "if_cpu": "CPU Usage",
            "if_mem": "Memory Usage",
            "if_rtt": "RTT spike / latency anomaly",
            "if_pkt_in": "Packet-In burst / possible DoS",
            "if_pkt_out": "Controller broadcast spike",
            "if_flow_mod": "Controller slow response",
            "if_table_occ": "Flow table saturation",
            "if_link_loss": "Link Degradation",
            "if_bw": "Bandwidth anomaly",
            "if_churn": "Flow churn anomaly",
            "if_zscore_avg": "Aggregate Z-Score",
            "if_ratio_pkt_flow": "PktIn/FlowMod Imbalance"
        }

        self.iso_features = list(self.pretty.keys())

    # -------------------------------------------------------------------
    # LSTM inference for temporal anomalies
    # -------------------------------------------------------------------
    def update_lstm(self, x8_features):

        self.buffer.append(x8_features)

        if len(self.buffer) < self.seq_len:
            return False, 0.0, []

        seq = np.array(self.buffer[-self.seq_len:])
        seq_scaled = self.lstm_scaler.transform(seq)
        X = np.expand_dims(seq_scaled, axis=0)

        pred = self.lstm_model.predict(X)[0]
        actual = seq_scaled[-1]

        # L2 prediction error
        error = np.linalg.norm(actual - pred)
        anomaly = error > self.lstm_threshold

        # feature-wise deviation
        abs_errors = np.abs(actual - pred)
        top_idx = np.argsort(abs_errors)[-3:][::-1]

        reasons = [self.lstm_feature_names[i] for i in top_idx]

        return anomaly, float(error), reasons

    # -------------------------------------------------------------------
    # Isolation Forest inference for structural anomalies
    # -------------------------------------------------------------------
    def update_if(self, x12_features):

        x_scaled = self.if_scaler.transform([x12_features])
        score = -self.if_model.decision_function(x_scaled)[0]
        anomaly = score > self.if_threshold
        
        # --- DETERMINISTIC OVERRIDE ---
        # If Link Loss (Index 7) is detected (value > 0), FORCE anomaly.
        # This handles cases where statistical variance is too low to trigger IF.
        link_loss_detected = x12_features[7] > 0
        if link_loss_detected:
            anomaly = True
            # artificially boost score to ensure it looks critical
            score = max(score, self.if_threshold + 0.1)

        # Compute z-score deviations
        # Simpler version: use raw deviation from mean
        # You can enhance it by saving means/stds during training
        z = x_scaled[0]  # approximate zscore

        top_idx = np.argsort(np.abs(z))[-3:][::-1]
        # Custom Diagnosis Logic for user-friendly output
        # If Packet-In (index 3) is a top contributor, force "DoS" label
        # even if Churn (index 9) is low (e.g. Ping Flood = 1 flow)
        
        reasons_refined = []
        for i in top_idx:
            # Index 3 is if_pkt_in (Packet-In)
            if i == 3 and z[3] > 2: 
                reasons_refined.append("DoS Attack (High Packet-In)")
            
            # Index 7 is if_link_loss (Link Failure)
            elif i == 7 and z[7] > 0:
                reasons_refined.append("Link Failure / Flap Detected")
            
            # Index 8 is Bandwidth
            elif i == 8:
                reasons_refined.append("Bandwidth Surge")
            
            else:
                reasons_refined.append(self.pretty[self.iso_features[i]])
                
        return anomaly, float(score), reasons_refined
