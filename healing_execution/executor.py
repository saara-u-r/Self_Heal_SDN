from healing_execution.action_library.restart_controller import restart_ryu
from healing_execution.action_library.reset_flows import reset_all_flows
from healing_execution.action_library.reroute_paths import reroute_paths
from healing_execution.state_manager.backup_state import backup_state
from healing_execution.state_manager.restore_state import restore_state

ACTION_REGISTRY = {
    "backup_state": backup_state,
    "restore_state": restore_state,
    "restart_controller": restart_ryu,
    "reset_flows": reset_all_flows,
    "reroute_paths": reroute_paths,
    "no_action": lambda: print("[EXECUTOR] No action required")
}

def execute_action(action_name):
    if action_name not in ACTION_REGISTRY:
        print(f"[EXECUTOR] Unknown action: {action_name}")
        return

    print(f"[EXECUTOR] Executing action: {action_name}")
    ACTION_REGISTRY[action_name]()

"""import time
import json

from healing_execution.action_library.restart_controller import restart_ryu
from healing_execution.action_library.reset_flows import reset_all_flows
from healing_execution.action_library.reroute_paths import reroute_paths
from healing_execution.action_library.reconnect_switch import reconnect_switch
from healing_execution.state_manager.backup_state import backup_state
from healing_execution.state_manager.restore_state import restore_state

LOG_FILE = "healing_execution/execution_logs/healing_log.json"

ACTION_MAP = {
    "backup_state": backup_state,
    "restore_state": restore_state,
    "restart_controller": restart_ryu,
    "reset_flows": reset_all_flows,
    "reroute_paths": reroute_paths,
    "reconnect_switch": lambda: reconnect_switch("s1"),
    "no_action": lambda: print("[EXECUTOR] No action required")
}

def log_action(entry):
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def execute_action(action):

    start = time.time()

    if action not in ACTION_MAP:
        print(f"[EXECUTOR] Unknown action: {action}")
        return

    print(f"[EXECUTOR] Executing action: {action}")
    ACTION_MAP[action]()

    duration = time.time() - start

    log_action({
        "action": action,
        "duration": duration
    })
"""