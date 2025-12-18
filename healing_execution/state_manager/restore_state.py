import json
from .state_store import FLOW_FILE, TOPO_FILE

def restore_state():
    print("[STATE] Restoring controller state")

    if FLOW_FILE.exists():
        with open(FLOW_FILE) as f:
            flows = json.load(f)
        print("[STATE] Flows restored:", flows)

    if TOPO_FILE.exists():
        with open(TOPO_FILE) as f:
            topo = json.load(f)
        print("[STATE] Topology restored:", topo)

    print("[STATE] State restoration completed")
