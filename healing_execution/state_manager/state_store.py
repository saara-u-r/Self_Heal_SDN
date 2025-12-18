from pathlib import Path

# ==============================
# Controller state storage
# ==============================

STATE_DIR = Path("controller_state")
STATE_DIR.mkdir(exist_ok=True)

FLOW_FILE = STATE_DIR / "flows.json"
TOPO_FILE = STATE_DIR / "topology.json"

# ==============================
# Healing execution shared state
# ==============================

# Keeps track of last healing time per fault (for cooldown)
LAST_ACTION_TIME = {}
