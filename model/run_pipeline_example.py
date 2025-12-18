# ============================================================
# run_pipeline_example.py
# Demonstrates how to run the full anomaly → diagnosis pipeline
# ============================================================

from anomaly_inference import AnomalyInference
from diagnosis_decision_engine import MLDecisionEngine

# Initialize
infer = AnomalyInference()
engine = MLDecisionEngine()

# Example input vectors (replace these with real-time data)
x8 =  [0.4, 0.3, 0.1, 0.9, 0.85, 0.2, 0.3, 0.7]#[1.5,30.2,0.005,0,0,0,0,0]    # LSTM features
x12 = [80, 70, 10, 12000, 11800, 20, 0.9, 0.01, 75, 5, 0.5, 1200000]#[1.5,30.2,0.005,0,0,0,0,0,0,0,0,0.0]  # IF features

# Step 1: LSTM inference
lstm_flag, lstm_error, lstm_reasons = infer.update_lstm(x8)
lstm_output = {
    "lstm_anomaly": lstm_flag,
    "error": lstm_error,
    "reasons": lstm_reasons
}

print("\n========== LSTM MODEL OUTPUT ==========")
print(f"LSTM Anomaly Detected : {lstm_flag}")
print(f"LSTM Prediction Error : {lstm_error:.4f}")
print(f"LSTM Top Deviations   : {lstm_reasons}")

# Step 2: IF inference
if_flag, if_score, if_reasons = infer.update_if(x12)
if_output = {
    "if_anomaly": if_flag,
    "score": if_score,
    "reasons": if_reasons
}

print("\n========== ISOLATION FOREST OUTPUT ==========")
print(f"IF Anomaly Detected   : {if_flag}")
print(f"IF Anomaly Score      : {if_score:.4f}")
print(f"IF Top Deviations     : {if_reasons}")

# Step 3: Decision engine
decision = engine.run(lstm_output, if_output)

print("\n========== DECISION OUTPUT ==========")
print(decision)

# from anomaly_inference import AnomalyInference
# from diagnosis_decision_engine import MLDecisionEngine

# infer = AnomalyInference()
# engine = MLDecisionEngine()

# def run_test(name, x8, x12):
#     print("\n==============================")
#     print(f"TEST CASE: {name}")
#     print("==============================")

#     # ---- LSTM ----
#     lstm_flag, lstm_error, lstm_reasons = infer.update_lstm(x8)
#     lstm_output = {
#         "lstm_anomaly": lstm_flag,
#         "error": lstm_error,
#         "reasons": lstm_reasons
#     }

#     print("\n[LSTM OUTPUT]")
#     print("Anomaly:", lstm_flag)
#     print("Error:", lstm_error)
#     print("Reasons:", lstm_reasons)

#     # ---- Isolation Forest ----
#     if_flag, if_score, if_reasons = infer.update_if(x12)
#     if_output = {
#         "if_anomaly": if_flag,
#         "score": if_score,
#         "reasons": if_reasons
#     }

#     print("\n[IF OUTPUT]")
#     print("Anomaly:", if_flag)
#     print("Score:", if_score)
#     print("Reasons:", if_reasons)

#     # ---- Decision Engine ----
#     decision = engine.run(lstm_output, if_output)

#     print("\n[FINAL DECISION]")
#     for k, v in decision.items():
#         print(f"{k}: {v}")

# # --------------------------------------------------------
# # TEST SAMPLES
# # --------------------------------------------------------

# # 1️⃣ NORMAL TRAFFIC
# x8_normal = [0.2, 0.3, 0.1, 0.15, 0.12, 0.10, 0.2, 0.25]
# x12_normal = [12, 30, 2, 40, 35, 5, 0.1, 0.001, 10, 1, 0.0, 20000]

# # 2️⃣ CPU SPIKE + PACKET-IN BURST (DoS)
# x8_attack = [0.95, 0.40, 0.20, 0.98, 0.97, 0.25, 0.3, 0.40]
# x12_attack = [95, 80, 5, 15000, 14900, 40, 0.2, 0.005, 90, 5, 3.0, 2e6]

# # 3️⃣ BANDWIDTH SURGE
# x8_bw = [0.3, 0.2, 0.15, 0.18, 0.14, 0.12, 0.18, 0.95]
# x12_bw = [20, 35, 3, 60, 55, 8, 0.1, 0.002, 150, 3, 0.0, 40000]

# # 4️⃣ FLOW TABLE SATURATION
# x8_flow = [0.4, 0.4, 0.2, 0.25, 0.20, 0.9, 0.85, 0.30]
# x12_flow = [40, 45, 4, 200, 180, 100, 0.95, 0.01, 20, 4, 0.0, 500000]

# # --------------------------------------------------------
# # RUN ALL TESTS
# # --------------------------------------------------------

# run_test("Normal Traffic", x8_normal, x12_normal)
# run_test("DoS Attack (CPU + PktIn Burst)", x8_attack, x12_attack)
# run_test("Bandwidth Surge", x8_bw, x12_bw)
# run_test("Flow Table Saturation", x8_flow, x12_flow)
