
import os
import numpy as np
import pandas as pd
import joblib

from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

# ==============================
# 0. CONFIG
# ==============================
SEED = 42
np.random.seed(SEED)

DATA_PATH = "training_data.csv"
ARTIFACTS_DIR = "ifmodels"      # <<<<<< SAVING HERE

os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# ==============================
# 1. LOAD DATA
# ==============================
df = pd.read_csv(DATA_PATH)

iso_features = [
    "if_cpu",
    "if_mem",
    "if_rtt",
    "if_pkt_in",
    "if_pkt_out",
    "if_flow_mod",
    "if_table_occ",
    "if_link_loss",
    "if_bw",
    "if_churn",
    "if_zscore_avg",
    "if_ratio_pkt_flow"
]

df_iso = df[iso_features].copy().dropna()
X = df_iso.values.astype(float)

print("Dataset loaded:", X.shape)

# ==============================
# 2. SCALING
# ==============================
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

joblib.dump(scaler, f"{ARTIFACTS_DIR}/if_scaler.pkl")
print("Scaler saved to:", f"{ARTIFACTS_DIR}/if_scaler.pkl")

# ==============================
# 3. TRAIN ISOLATION FOREST
# ==============================
iso_forest = IsolationForest(
    n_estimators=300,
    contamination="auto",
    max_features=1.0,
    n_jobs=-1,
    random_state=SEED
)

print("\nTraining Isolation Forest...")
iso_forest.fit(X_scaled)

joblib.dump(iso_forest, f"{ARTIFACTS_DIR}/isolation_forest_model.pkl")
print("Model saved to:", f"{ARTIFACTS_DIR}/isolation_forest_model.pkl")

# ==============================
# 4. SCORES & THRESHOLD
# ==============================
scores = iso_forest.decision_function(X_scaled)
anomaly_scores = -scores

threshold = float(np.percentile(anomaly_scores, 99))
custom_labels = (anomaly_scores >= threshold).astype(int)

print("\nThreshold (99th percentile):", threshold)
print("Detected anomalies:", custom_labels.sum())

joblib.dump({
    "threshold": threshold,
    "scores": anomaly_scores,
    "features": iso_features
}, f"{ARTIFACTS_DIR}/if_threshold_info.pkl")
print("Threshold info saved.")

# ==============================
# 5. ANALYSIS BASELINES
# ==============================
normal_mask = custom_labels == 0
normal_scaled = X_scaled[normal_mask]
normal_unscaled = X[normal_mask]

median_unscaled = np.median(normal_unscaled, axis=0)
means_scaled = normal_scaled.mean(axis=0)
stds_scaled = normal_scaled.std(axis=0) + 1e-6

pretty = {
    "if_cpu": "CPU Usage",
    "if_mem": "Memory Usage",
    "if_rtt": "RTT (Latency)",
    "if_pkt_in": "Packet-In Rate",
    "if_pkt_out": "Packet-Out Rate",
    "if_flow_mod": "Flow-Mod Rate",
    "if_table_occ": "Flow Table Occupancy",
    "if_link_loss": "Link Packet Loss",
    "if_bw": "Bandwidth",
    "if_churn": "Flow Churn",
    "if_zscore_avg": "Aggregate Z-Score",
    "if_ratio_pkt_flow": "PktIn/FlowMod Ratio"
}

def diagnose(z):
    msg = []
    if z[3] > 2 and z[9] > 2: msg.append("Possible DoS / High Packet-In + Churn")
    if z[2] > 2 or z[7] > 2: msg.append("RTT Spike / Link Degradation")
    if z[6] > 2: msg.append("Flow Table Saturation")
    if z[5] < -2 and z[3] > 2: msg.append("Controller Slow Response")
    if z[8] > 2: msg.append("High Bandwidth Surge")
    if z[0] > 2 or z[1] > 2: msg.append("Controller CPU/Mem Overload")
    return " | ".join(msg) if msg else "General Structural Outlier"

# ==============================
# 6. ANOMALY EXPLANATIONS
# ==============================
print("\n==============================")
print(" ANOMALY EXPLANATIONS")
print("==============================\n")

for idx, is_anom in enumerate(custom_labels):
    if not is_anom:
        continue

    row_scaled = X_scaled[idx]
    row_unscaled = X[idx]

    zscores = (row_scaled - means_scaled) / stds_scaled
    top3 = np.argsort(np.abs(zscores))[-3:][::-1]

    print(f"\n⚠️ Anomaly at index {idx} (score = {anomaly_scores[idx]:.4f})")

    for f_idx in top3:
        col = iso_features[f_idx]
        name = pretty[col]

        actual = row_unscaled[f_idx]
        median = median_unscaled[f_idx]
        diff = actual - median
        z = zscores[f_idx]

        direction = "HIGH" if z > 0 else "LOW"
        severity = "VERY " if abs(z) > 3 else ""

        print(f"  • {name}:")
        print(f"      - Actual value     : {actual:.4f}")
        print(f"      - Median normal    : {median:.4f}")
        print(f"      - Difference       : {diff:+.4f}")
        print(f"      - Deviation        : {severity}{direction} ({z:.2f}σ)\n")

    print("  → Diagnosis:", diagnose(zscores))
    print("-" * 50)

print("\n✅ Isolation Forest + Detailed Explanations COMPLETE")
print("All files saved inside: ifmodels/")
