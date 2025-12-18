from healing_execution.workflow_engine import run_healing_workflow


# Fake decision (simulating ML + diagnosis output)
decision = {
    "fault": "controller_latency",
    "severity": "critical"
}

run_healing_workflow(decision)
