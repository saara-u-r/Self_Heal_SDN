#“This module performs controller-level healing by restarting the SDN control plane.”
import os
import time
import shutil
import subprocess
import sys

# Get Project Root relative to this file
# This file: healing_execution/action_library/restart_controller.py
# Root: ../../
ACTION_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(ACTION_LIB_DIR, "..", ".."))

RYU_VENV_BIN = os.path.join(PROJECT_ROOT, "ryu_venv", "bin", "ryu-manager")

def restart_ryu():
    """
    Restarts the Ryu controller using the PROJECT VIRTUAL ENV.
    """

    print("[ACTION] Restarting Ryu Controller...")
    
    if not os.path.exists(RYU_VENV_BIN):
        print(f"[ERROR] Ryu Venv binary not found at: {RYU_VENV_BIN}")
        return

    # 1. Kill existing process
    print("[ACTION] Killing existing Ryu process...")
    os.system("pkill -f ryu-manager")
    time.sleep(2)

    # 2. Start new process using the VENV binary
    # We must run it from the controller_apps directory effectively
    controller_app = os.path.join(PROJECT_ROOT, "controller_apps", "sh_controller.py")
    
    print(f"[ACTION] Starting Ryu from: {RYU_VENV_BIN}")
    
    # Run in background (nohup equivalent) 
    # Note: This is complex because we are calling this from the Healing Agent 
    # which is running in its own terminal.
    # Ideally, we should restart it in the SEPARATE Controller terminal window.
    # But we can't easily inject commands into another gnome-terminal tab.
    # So we will just launch it as a subprocess here. 
    # OR better: The user will lose the logs in the "Controller" tab, 
    # but the process will run.
    
    args = [
        RYU_VENV_BIN,
        controller_app,
        "ryu.app.ofctl_rest",
        "--verbose",
        "--ofp-tcp-listen-port", "6633"
    ]
    
    # We use Popen so it doesn't block
    subprocess.Popen(args, cwd=os.path.join(PROJECT_ROOT, "controller_apps"))

    print("[ACTION] Ryu Controller restarted successfully (New PID)")
