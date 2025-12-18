import time
import json
import os
import sys

# Add project root to path to find healing_execution module
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.append(PROJECT_ROOT)

from healing_execution.workflow_engine import run_healing_workflow

LOG_FILE = os.path.join(PROJECT_ROOT, "monitoring_and_telemetry", "logs", "anomaly_decisions.json")

def tail_f(filename):
    """Generates new lines from a file as they are written."""
    # WaitForFile
    while not os.path.exists(filename):
        print(f"[LISTENER] Waiting for log file: {filename}...")
        time.sleep(2)

    with open(filename, 'r') as f:
        # Go to the end of file
        f.seek(0, 2)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            yield line

def main():
    print("========================================")
    print("   SELF-HEALING EXECUTION AGENT")
    print("   Monitoring Decision Logs...")
    print("========================================")

    for line in tail_f(LOG_FILE):
        try:
            if not line.strip():
                continue
                
            decision = json.loads(line)
            fault = decision.get("fault", "normal")
            action = decision.get("recommended_action", "monitor")
            
            # Filter out noise
            if action in ["monitor", "no_action"]:
                # Optional: distinct output for normal heartbeat
                # print(f".", end="", flush=True) 
                continue

            print(f"\n[ALERT] Detected: {fault} | Action: {action}")
            run_healing_workflow(decision)
            print("-" * 40)

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
