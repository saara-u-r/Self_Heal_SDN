# Self-Healing SDN Controller Framework

## Project Overview
This project serves as a research framework for **Autonomous Network Management**. It integrates Software-Defined Networking (SDN) with Machine Learning to creates a closed-loop control system that can:
1.  **Monitor** the network in real-time.
2.  **Detect** anomalies (DoS, Link Failures, Congestion) using trained ML models.
3.  **Diagnose** the root cause using an Expert Decision Engine.
4.  **Heal** the network automatically.

The system uses a **Hybrid AI Approach**, combining **LSTM (Long Short-Term Memory)** networks for temporal sequence analysis, **Isolation Forests** for outlier detection, and **Deterministic Rules** for critical state validation.

---

## System Architecture

The framework is composed of three decoupled layers working in parallel:

### 1. Infrastructure Layer (The Network)
*   **Mininet**: Simulates the physical data plane comprising hosts, switches, and links.
*   **Topology**: A custom "Triangle Loop" topology with redundant paths (`s1-s2`, `s2-s3`, `s3-s1`) to allow for path recovery testing.
*   **Ryu Controller**: The brain of the SDN. It runs a custom application (`sh_controller.py`) that:
    *   Manages OpenFlow flow rules.
    *   Tracks **Port Status Events** to detect link flaps immediately.
    *   Exposes a comprehensive **Rest API** (`/stats/sh_features`) for external polling.

### 2. Monitoring Layer (Telemetry Agent)
*   **Telemetry Agent**: A standalone Python service (`telemetry_agent.py`) that acts as the "Sensory Cortex".
*   **Feature Engineering**: It polls the Controller and Linux Kernel interfaces (`/sys/class/net`) to measure:
    *   **Traffic Rates**: Packet-In, Packet-Out, Bandwidth (Bytes/sec).
    *   **System Health**: CPU, RAM, and Control Plane Latency (RTT).
    *   **Derived Metrics**: Z-Scores (Standard Deviation) and Flow Efficiency Ratios.

### 3. ML Analysis Layer (The Brain)
*   **Real-Time Pipeline**: A loop (`run_realtime_pipeline.py`) that ingests live telemetry and feeds it into the models.
*   **Model 1: LSTM (Temporal)**:
    *   *Purpose*: Detects anomalies that evolve over time (e.g., slow memory leaks, gradually increasing latency).
    *   *Input*: A sequence of the last 10 data points.
*   **Model 2: Isolation Forest (Structural)**:
    *   *Purpose*: Detects immediate "Shape" outliers (e.g., massive Packet-In packet with zero Flow-Mods).
    *   *Input*: Immediate snapshot of system state.
*   **Decision Engine**: A rule-based classifier (`diagnosis_decision_engine.py`) that interprets the raw model outputs. It prioritizes critical alerts (e.g., "DoS Detected") over noise (e.g., "Bandwidth Surge") to prevent alert fatigue.

---

## Directory Structure
```text
self-heal-sdn/
├── controller_apps/
│   └── sh_controller.py       # SDN Controller Logic (Ryu)
├── mininet_topology/
│   └── topo_healing.py        # Custom Mininet Topology
├── model/
│   ├── lstm_final.py          # LSTM Training Script
│   ├── isolationForest.py     # Isolation Forest Training Script
│   ├── run_realtime_pipeline.py # MAIN PIPELINE: Inference Loop
│   ├── anomaly_inference.py   # Inference Logic Class
│   ├── diagnosis_decision_engine.py # Decision prioritization logic
│   ├── lstmModels/            # Trained LSTM weights
│   └── ifmodels/              # Trained IF weights
├── monitoring_and_telemetry/
│   ├── logs/
│   │   ├── training_data.csv  # The dataset used for training
│   │   └── anomaly_decisions.json # LIVE OUTPUT for Self-Healing
│   └── telemetry_agent.py     # Metric Collection Agent
├── run_project.sh             # Master Startup Script
└── README.md
```

---

## How to Run

### Automated Startup
We have provided a unified script that handles Virtual Environment creation, Dependency installation, Model Training (if needed), and Process orchestration.

```bash
./run_project.sh
```
*   **Terminal Output**: You will see live logs from the Controller, Agent, and ML Pipeline.
*   **Mininet CLI**: You will be dropped into the `mininet>` shell to run tests.

### Output Location
All decisions are logged in real-time JSONL format for consumption by the future Self-Healing layer:
> `monitoring_and_telemetry/logs/anomaly_decisions.json`

---

## Verification & Attack Simulation

Once the system is running, use these commands in the Mininet CLI to test defenses:

### 1. DDoS Attack Simulation
**Scenario**: Host `h1` floods the controller with random packets.

**Expected Result**: System detects "DoS Attack" / "Packet-In Burst".
```bash
mininet> h1 ping -f h2
# OR
mininet> h1 hping3 -S -p 80 --flood 10.0.0.2
```

### 2. Link Failure (Physical Cut)
**Scenario**: The link between Switch 1 and Switch 2 is severed.

**Expected Result**: 
1. Controller receives `PortStatus` event.
2. ML Pipeline detects "Link Failure".
3. Controller clears MAC table to re-learn paths.
```bash
mininet> link s1 s2 down
# Restore with:
mininet> link s1 s2 up
```

### 3. Bandwidth Congestion
**Scenario**: Heavy file transfer between hosts.

**Expected Result**: System detects "Bandwidth Surge".
```bash
mininet> iperf h2 h3
```

---

## Prerequisites
*   Ubuntu 20.04/22.04 or compatible Linux
*   Python 3.8+
*   Mininet
*   Ryu SDN Manager
*   TensorFlow / Scikit-Learn
