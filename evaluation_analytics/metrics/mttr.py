import json

LOG_FILE = "healing_execution/execution_logs/healing_log.json"

def compute_mttr():
    durations = []

    with open(LOG_FILE) as f:
        for line in f:
            entry = json.loads(line)
            if "duration" in entry:
                durations.append(entry["duration"])

    if not durations:
        return 0.0

    return sum(durations) / len(durations)
