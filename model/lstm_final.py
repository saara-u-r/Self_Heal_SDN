
# The LSTM’s training R² appears low because recurrent networks use dropout, overlap heavily between sequences,
#  and predict the next timestep based on noisy inputs. However, the high validation R² (~0.98) 
# shows that the model generalizes extremely well and accurately learns temporal patterns. 
# This behavior is normal and expected for forecasting-based anomaly detection.

import os
import numpy as np
import pandas as pd
import joblib
import tensorflow as tf

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import ModelCheckpoint

# ==============================
# 0. Reproducibility
# ==============================
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

# ==============================
# 1. Config
# ==============================
DATA_PATH = "training_data.csv"
ARTIFACTS_DIR = "lstmModels"   # <-- save everything here

SEQ_LEN = 20
BATCH_SIZE = 64
EPOCHS = 100   # full training, no early stopping

os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# ==============================
# 2. R² Metric (optional but useful)
# ==============================
def r2_metric(y_true, y_pred):
    ss_res = tf.reduce_sum(tf.square(y_true - y_pred))
    ss_tot = tf.reduce_sum(tf.square(y_true - tf.reduce_mean(y_true)))
    return 1.0 - ss_res / (ss_tot + tf.keras.backend.epsilon())

# ==============================
# 3. Build LSTM model
# ==============================
def build_lstm_model(seq_len: int, num_features: int):
    model = Sequential()
    model.add(LSTM(64, input_shape=(seq_len, num_features), return_sequences=True))
    model.add(Dropout(0.2))
    model.add(LSTM(32, return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(num_features))  # predict all 8 features at t+1

    model.compile(
        loss="mse",
        optimizer="adam",
        metrics=["mae", r2_metric]
    )
    return model

# ==============================
# 4. Create sequences
# ==============================
def create_sequences(data_array, seq_len=20):
    X, y = [], []
    for i in range(len(data_array) - seq_len):
        X.append(data_array[i:i+seq_len])
        y.append(data_array[i+seq_len])
    return np.array(X), np.array(y)

# ==============================
# 5. Main training flow
# ==============================
def main():

    # ------------------------------
    # 5.1 Load Data
    # ------------------------------
    df = pd.read_csv(DATA_PATH)

    lstm_features = [
        "lstm_cpu",
        "lstm_mem",
        "lstm_rtt",
        "lstm_pkt_in",
        "lstm_pkt_out",
        "lstm_flow_mod",
        "lstm_flows_sec",
        "lstm_bw"
    ]

    df = df[lstm_features]
    df = df.dropna()

    data = df.astype(float).values

    # ------------------------------
    # 5.2 Scale data
    # ------------------------------
    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(data)

    scaler_path = os.path.join(ARTIFACTS_DIR, "lstm_scaler.pkl")
    joblib.dump(scaler, scaler_path)
    print(f"Scaler saved to: {scaler_path}")

    # ------------------------------
    # 5.3 Prepare sequences
    # ------------------------------
    X, y = create_sequences(data_scaled, SEQ_LEN)
    print("X shape:", X.shape)
    print("y shape:", y.shape)

    # ------------------------------
    # 5.4 Time-based split
    # ------------------------------
    split = int(0.8 * len(X))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print("Train samples:", X_train.shape[0])
    print("Val samples:", X_val.shape[0])

    # ------------------------------
    # 5.5 Build and train model (FULL training)
    # ------------------------------
    num_features = X.shape[2]
    model = build_lstm_model(SEQ_LEN, num_features)
    model.summary()

    checkpoint_path = os.path.join(ARTIFACTS_DIR, "lstm_best_model.h5")
    checkpoint = ModelCheckpoint(
        filepath=checkpoint_path,
        monitor="val_loss",
        save_best_only=True,
        verbose=1
    )

    print("\n🚀 Training for all epochs (no early stopping)...\n")

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=[checkpoint],
        shuffle=False
    )

    final_model_path = os.path.join(ARTIFACTS_DIR, "lstm_final_model.h5")
    model.save(final_model_path)

    print(f"\nFinal model saved to: {final_model_path}")
    print(f"Best model (by val_loss) saved to: {checkpoint_path}")

    # ------------------------------
    # 5.6 Compute L2 prediction errors
    # ------------------------------
    y_val_pred = model.predict(X_val)

    l2_errors = np.linalg.norm(y_val - y_val_pred, axis=1)

    print("\nPrediction L2 error stats:")
    print("min:", float(np.min(l2_errors)))
    print("max:", float(np.max(l2_errors)))
    print("mean:", float(np.mean(l2_errors)))

    threshold = float(np.mean(l2_errors) + 3 * np.std(l2_errors))
    print("Suggested anomaly threshold:", threshold)

    anomaly_labels = (l2_errors > threshold).astype(int)
    print("Number of anomalies in val set:", int(anomaly_labels.sum()))

    # ------------------------------
    # 5.7 Save threshold + errors
    # ------------------------------
    thr_file = os.path.join(ARTIFACTS_DIR, "lstm_threshold_info.pkl")
    joblib.dump(
        {"threshold": threshold, "val_l2_errors": l2_errors},
        thr_file
    )
    print(f"Threshold info saved to: {thr_file}\n")

    # ==============================
    # 5.8 Detailed deviation analysis per anomaly
    # ==============================
    feature_names = [
        "CPU Usage",
        "Memory Usage",
        "RTT (Latency)",
        "Packet-In Rate",
        "Packet-Out Rate",
        "Flow-Mod Rate",
        "Flows per second",
        "Bandwidth"
    ]

    print("\n==============================")
    print(" LSTM ANOMALY EXPLANATIONS")
    print("==============================\n")

    # helper to infer reason from feature & diff
    def reason(feature, diff):
        if feature == "CPU Usage":
            return "CPU spike / overload"
        if feature == "Memory Usage":
            return "Memory leak or sudden increase"
        if feature == "RTT (Latency)":
            return "RTT spike / latency anomaly"
        if feature == "Packet-In Rate":
            return "Packet-In burst / possible DoS"
        if feature == "Packet-Out Rate":
            return "Controller broadcast spike"
        if feature == "Flow-Mod Rate":
            return "Controller slow to install rules"
        if feature == "Flows per second":
            return "Flow churn anomaly"
        if feature == "Bandwidth":
            return "Sudden traffic surge/drop"
        return "General temporal deviation"

    # per-feature absolute errors
    abs_errors = np.abs(y_val - y_val_pred)

    for idx, is_anom in enumerate(anomaly_labels):
        if not is_anom:
            continue

        print(f"\n⚠️ Anomaly at validation index {idx}  (L2 error = {l2_errors[idx]:.4f})")

        errors = abs_errors[idx]
        top3_idx = np.argsort(errors)[-3:][::-1]

        for f_idx in top3_idx:
            fname = feature_names[f_idx]
            actual = y_val[idx][f_idx]
            pred = y_val_pred[idx][f_idx]
            diff = actual - pred

            print(f"  • {fname}:")
            print(f"      - Actual value   : {actual:.5f}")
            print(f"      - Predicted value: {pred:.5f}")
            print(f"      - Difference     : {diff:+.5f}")
            print(f"      - Reason         : {reason(fname, diff)}\n")

    print("\n✅ LSTM training + anomaly explanation complete.")
    print("All artifacts saved in:", ARTIFACTS_DIR)


if __name__ == "__main__":
    main()
