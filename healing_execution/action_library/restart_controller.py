#“This module performs controller-level healing by restarting the SDN control plane.”
import os
import time
import shutil
import subprocess

def restart_ryu():
    """
    Restarts the Ryu controller if available.
    Otherwise, simulates restart (for macOS testing).
    """

    print("[ACTION] Restarting Ryu Controller...")

    ryu_path = shutil.which("ryu-manager")

    if ryu_path is None:
        # Mock behavior for macOS / development
        print("[MOCK] ryu-manager not found")
        print("[MOCK] Simulating controller restart")
        time.sleep(2)
        print("[MOCK] Controller restart simulation complete")
        return

    # Real restart (for Linux / VM)
    os.system("pkill -f ryu-manager")
    time.sleep(2)

    subprocess.Popen([
        ryu_path,
        "controller_apps/sh_controller.py"
    ])

    print("[ACTION] Ryu Controller restarted successfully")
