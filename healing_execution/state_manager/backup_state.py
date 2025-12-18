import json
from .state_store import FLOW_FILE, TOPO_FILE

def backup_state():
    print("[STATE] Backing up controller state")

    with open(FLOW_FILE, "w") as f:
        json.dump({"flows": "backup_placeholder"}, f)

    with open(TOPO_FILE, "w") as f:
        json.dump({"topology": "backup_placeholder"}, f)

    print("[STATE] Backup completed")
