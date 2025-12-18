# ============================================================
# MODEL-DRIVEN DIAGNOSIS + DECISION ENGINE (CONNECTED TO HEALING)
# ============================================================

from healing_execution.workflow_engine import run_healing_workflow


class MLDecisionEngine:

    def __init__(self):

        # ---------------------------
        # Mapping: model reason → anomaly type
        # ---------------------------
        self.reason_to_type = {

            # LSTM / IF interpretations
            "CPU spike / overload": "cpu_overload",
            "Memory leak or sudden increase": "memory_leak",
            "RTT spike / latency anomaly": "rtt_spike",
            "Packet-In burst / possible DoS": "packet_in_burst",
            "Controller broadcast spike": "controller_broadcast_spike",
            "Flow churn anomaly": "flow_churn_spike",
            "Bandwidth anomaly": "bandwidth_surge",

            # IF reason mappings
            "Flow table saturation": "flow_table_full",
            "High Bandwidth Surge": "bandwidth_surge",
            "CPU/Mem Overload": "cpu_overload",
            "Possible DoS / High Packet-In + Churn": "packet_in_burst",
            "RTT Spike / Link Degradation": "rtt_spike",
            "Controller Slow Response": "controller_slow",
            "Link Failure / Flap Detected": "link_failure",
        }

        # ---------------------------
        # Healing action + severity mapping
        # ---------------------------
        self.action_map = {
            "cpu_overload": ("restart_controller", "High CPU deviation detected", "HIGH"),
            "memory_leak": ("restart_module", "Memory usage deviated abnormally", "HIGH"),
            "rtt_spike": ("reroute_paths", "High RTT / latency anomaly", "MEDIUM"),
            "link_failure": ("reroute_paths", "Link Failure confirmed", "CRITICAL"),
            "packet_in_burst": ("enable_rate_limit", "Possible DoS detected", "CRITICAL"),
            "controller_broadcast_spike": ("optimize_flow_rules", "Packet-Out anomaly", "MEDIUM"),
            "flow_churn_spike": ("rebalance_flows", "Flow churn anomaly", "MEDIUM"),
            "bandwidth_surge": ("load_balance", "Bandwidth deviation", "MEDIUM"),
            "flow_table_full": ("reset_flows", "Flow table saturation", "CRITICAL"),
            "controller_slow": ("restart_controller", "Controller slow response", "HIGH"),
            "general_outlier": ("monitor", "Unclassified anomaly", "LOW"),
            "normal": ("no_action", "No anomaly detected", "LOW")
        }

    # ---------------------------------------------------------
    # Classify anomaly type
    # ---------------------------------------------------------
    def classify_anomaly(self, lstm_reasons, if_reasons):

        combined = lstm_reasons + if_reasons
        if not combined:
            return "normal", "No deviation detected"

        detected_types = []
        for r in combined:
            if r in self.reason_to_type:
                detected_types.append(self.reason_to_type[r])

        # Priority-based classification
        if "packet_in_burst" in detected_types:
            return "packet_in_burst", "DoS / Packet-In Storm"

        if "link_failure" in detected_types:
            return "link_failure", "Link Failure Detected"

        if "cpu_overload" in detected_types:
            return "cpu_overload", "CPU Overload"

        if "rtt_spike" in detected_types:
            return "rtt_spike", "Latency Spike"

        # Fallback
        return detected_types[0], combined[0]

    # ---------------------------------------------------------
    # Main pipeline
    # ---------------------------------------------------------
    def run(self, lstm_output, if_output):

        lstm_flag = lstm_output.get("lstm_anomaly", False)
        if_flag = if_output.get("if_anomaly", False)

        # CASE 1: No anomaly
        if not lstm_flag and not if_flag:
            decision = {
                "fault": "normal",
                "severity": "LOW"
            }
            return decision

        lstm_reasons = lstm_output.get("reasons", [])
        if_reasons = if_output.get("reasons", [])

        anomaly_type, matched_reason = self.classify_anomaly(
            lstm_reasons, if_reasons
        )

        action, why_action, severity = self.action_map.get(
            anomaly_type, ("monitor", "Unclassified anomaly", "LOW")
        )

        # ---------------------------
        # FINAL DECISION OBJECT
        # ---------------------------
        decision = {
            "fault": anomaly_type,
            "severity": severity,
            "recommended_action": action,
            "why_detected": matched_reason,
            "why_action": why_action
        }

        return decision


# ============================================================
# DIRECT EXECUTION (PIPELINE INTEGRATION)
# ============================================================
if __name__ == "__main__":

    # ---- Simulated ML outputs (replace with real ones) ----
    lstm_output = {
        "lstm_anomaly": True,
        "reasons": ["CPU spike / overload"]
    }

    if_output = {
        "if_anomaly": False,
        "reasons": []
    }

    engine = MLDecisionEngine()
    decision = engine.run(lstm_output, if_output)

    print("\n[DIAGNOSIS] Decision Produced:")
    for k, v in decision.items():
        print(f"  {k}: {v}")

    print("\n[DIAGNOSIS] Triggering Healing Execution\n")

    # 🔴 ACTUAL CONNECTION TO HEALING EXECUTION
    run_healing_workflow(decision)
