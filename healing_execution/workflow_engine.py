import yaml
from healing_execution.executor import execute_action
from healing_execution.state_manager.cooldown import is_in_cooldown
from evaluation_analytics.mttr_history import average_mttr
import os

# Get absolute path to the project root (assuming this file is in healing_execution/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
POLICY_FILE = os.path.join(PROJECT_ROOT, "config", "healing_policy.yaml")

def load_policies():
    with open(POLICY_FILE) as f:
        return yaml.safe_load(f)

def run_healing_workflow(decision):

    fault = decision["fault"]
    severity = decision["severity"]

    policies = load_policies()
    policy = policies.get(fault, policies.get("normal"))

    cooldown = policy.get("cooldown", 0)
    workflow = policy["workflow"]

    if is_in_cooldown(fault, cooldown):
        print(f"[WORKFLOW] Healing skipped (cooldown active for {fault})")
        return

    print(f"[WORKFLOW] Executing workflow for {fault} | Severity: {severity}")

    for step in workflow:
        execute_action(step)

    print("[WORKFLOW] Healing workflow completed")
