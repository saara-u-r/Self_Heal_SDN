import time
import pandas as pd
from anomaly_inference import AnomalyInference
from diagnosis_decision_engine import MLDecisionEngine
import yaml

import os

# ---------------- LOAD CONFIG ----------------
# Resolve paths relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "../monitoring_and_telemetry/config/settings.yaml")

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# CSV path is relative to the monitoring_and_telemetry root (where config is usually relative to)
# Config says "logs/training_data.csv", which is inside monitoring_and_telemetry
TELEMETRY_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../monitoring_and_telemetry"))
CSV_FILENAME = config['telemetry']['csv_path']
CSV_PATH = os.path.join(TELEMETRY_ROOT, CSV_FILENAME)
POLL_INTERVAL = config['controller']['poll_interval']

# ---------------- INIT MODELS ----------------
infer = AnomalyInference()
engine = MLDecisionEngine()

print("[*] Real-Time Anomaly Pipeline Started")

last_timestamp = None

while True:
    try:
        # Read last row only (efficient)
        df = pd.read_csv(CSV_PATH)

        if df.empty:
            time.sleep(1)
            continue

        row = df.iloc[-1]

        # Avoid reprocessing same data
        if last_timestamp == row['timestamp']:
            time.sleep(1)
            continue

        last_timestamp = row['timestamp']

        # ---------------- BUILD FEATURE VECTORS ----------------

        x8 = [
            row['lstm_cpu'],
            row['lstm_mem'],
            row['lstm_rtt'],
            row['lstm_pkt_in'],
            row['lstm_pkt_out'],
            row['lstm_flow_mod'],
            row['lstm_flows_sec'],
            row['lstm_bw']
        ]

        x12 = [
            row['if_cpu'],
            row['if_mem'],
            row['if_rtt'],
            row['if_pkt_in'],
            row['if_pkt_out'],
            row['if_flow_mod'],
            row['if_table_occ'],
            row['if_link_loss'],
            row['if_bw'],
            row['if_churn'],
            row['if_zscore_avg'],
            row['if_ratio_pkt_flow']
        ]

        # ---------------- LSTM INFERENCE ----------------
        lstm_flag, lstm_error, lstm_reasons = infer.update_lstm(x8)

        lstm_output = {
            "lstm_anomaly": lstm_flag,
            "error": lstm_error,
            "reasons": lstm_reasons
        }

        # ---------------- IF INFERENCE ----------------
        if_flag, if_score, if_reasons = infer.update_if(x12)

        if_output = {
            "if_anomaly": if_flag,
            "score": if_score,
            "reasons": if_reasons
        }

        # ---------------- DECISION ENGINE ----------------
        decision = engine.run(lstm_output, if_output)
        
        # ---------------- LOGGING TO FILE ----------------
        # Save for Self-Healing Layer
        decision['timestamp'] = time.time()
        
        # Path: monitoring_and_telemetry/logs/anomaly_decisions.json
        log_dir = os.path.join(script_dir, '..', 'monitoring_and_telemetry', 'logs')
        log_file = os.path.join(log_dir, 'anomaly_decisions.json')
        
        # Ensure dir exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Append as one JSON object per line (JSONL format)
        with open(log_file, 'a') as f:
            f.write(json.dumps(decision) + "\n")

        # ---------------- LIVE OUTPUT ----------------
        print("\n================ LIVE DECISION ================")
        print(f"Time           : {row['timestamp']}")
        print(f"LSTM Anomaly   : {lstm_flag} | Error: {lstm_error:.4f}")
        print(f"IF Anomaly     : {if_flag} | Score: {if_score:.4f}")
        print("Final Decision:", decision)

        time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\nStopping real-time pipeline...")
        break

    except Exception as e:
        print("Error:", e)
        time.sleep(1)
