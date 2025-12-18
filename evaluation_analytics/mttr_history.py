import json
from statistics import mean

LOG_FILE = "healing_execution/execution_logs/healing_log.json"

def average_mttr(action):
    times = []

    with open(LOG_FILE) as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("action") == action:
                times.append(entry["duration"])

    return mean(times) if times else float("inf")
