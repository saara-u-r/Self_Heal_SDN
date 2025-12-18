#!/bin/bash
set -e

PROJECT_ROOT="$PWD"
RYU_VENV="$PROJECT_ROOT/ryu_venv"
AGENT_DIR="$PROJECT_ROOT/monitoring_and_telemetry"
AGENT_VENV="$AGENT_DIR/.venv"
MODEL_DIR="$PROJECT_ROOT/model"
MODEL_VENV="$MODEL_DIR/.venv"

# Cleanup
echo "[*] Cleaning up old processes..."
sudo mn -c 2>/dev/null || true
sudo killall ryu-manager 2>/dev/null || true
sudo killall python3 2>/dev/null || true

# --- SETUP FUNCTIONS ---

setup_ryu() {
    if [ ! -d "$RYU_VENV" ]; then
        echo "[*] Creating Ryu Venv (Python 3.8)..."
        # Ryu requires Python 3.8 due to eventlet issues
        python3.8 -m venv "$RYU_VENV"
        source "$RYU_VENV/bin/activate"
        pip install --upgrade pip
        pip install "setuptools<58.0.0" "wheel"
        pip install ryu eventlet==0.30.2
        deactivate
    fi
}

setup_agent() {
    if [ ! -d "$AGENT_VENV" ]; then
        echo "[*] Creating Agent Venv (Python 3.8)..."
        python3.8 -m venv "$AGENT_VENV"
        source "$AGENT_VENV/bin/activate"
        pip install --upgrade pip
        pip install -r "$AGENT_DIR/requirements.txt"
        deactivate
    fi
}

setup_model() {
    if [ ! -d "$MODEL_VENV" ]; then
        echo "[*] Creating Model Venv (Python 3.8)..."
        python3.8 -m venv "$MODEL_VENV"
        source "$MODEL_VENV/bin/activate"
        pip install --upgrade pip
        # Install deps (simplified list based on script)
        pip install tensorflow pandas numpy scikit-learn joblib pyyaml h5py
        deactivate
    fi
}

# --- CHECK & TRAIN MODELS ---
train_models() {
    if [ ! -f "$MODEL_DIR/lstmModels/lstm_final_model.h5" ] || [ ! -f "$MODEL_DIR/ifmodels/isolation_forest_model.pkl" ]; then
        echo "[*] Models not found. Starting Training..."
        source "$MODEL_VENV/bin/activate"
        cd "$MODEL_DIR"
        python lstm_final.py
        python isolationForest.py
        cd "$PROJECT_ROOT"
        deactivate
        echo "[*] Training Complete."
    else
        echo "[*] Models already trained."
    fi
}

# --- MAIN EXECUTION ---

echo "[*] Setting up environments..."
# 1. Setup Venvs
setup_ryu
setup_agent
setup_model

# 2. Train Models if needed
train_models

# Export env vars for all terminals
export PROJECT_ROOT
export PYTHONPATH="$PROJECT_ROOT"
export PYTHONUNBUFFERED=1

# 3. Start Ryu Controller
echo "[*] Starting Ryu Controller..."
gnome-terminal --tab --title="Controller" -- bash -c "
    source '$RYU_VENV/bin/activate'; 
    cd controller_apps; 
    echo 'Starting Ryu...';
    \"$RYU_VENV/bin/ryu-manager\" sh_controller.py ryu.app.ofctl_rest --verbose --ofp-tcp-listen-port 6633; 
    exec bash"

# Wait for Controller
sleep 5

# 4. Start Telemetry Agent
echo "[*] Starting Telemetry Agent..."
gnome-terminal --tab --title="Telemetry" -- bash -c "
    export PYTHONPATH='$PROJECT_ROOT';
    export PYTHONUNBUFFERED=1;
    source '$AGENT_VENV/bin/activate'; 
    cd monitoring_and_telemetry; 
    echo 'Starting Telemetry Agent...';
    python3 telemetry_agent.py; 
    exec bash"

# 5. Start ML Pipeline
echo "[*] Starting Real-Time ML Pipeline..."
gnome-terminal --tab --title="ML Pipeline" -- bash -c "
    export PYTHONPATH='$PROJECT_ROOT';
    export PYTHONUNBUFFERED=1;
    source '$MODEL_VENV/bin/activate'; 
    cd model; 
    echo 'Starting ML Pipeline...';
    python run_realtime_pipeline.py; 
    exec bash"

# 6. Start Healing Listener (New 4th Terminal)
echo "[*] Starting Healing Agent..."
gnome-terminal --tab --title="Healing Agent" -- bash -c "
    export PYTHONPATH='$PROJECT_ROOT';
    export PYTHONUNBUFFERED=1;
    source '$MODEL_VENV/bin/activate'; 
    cd healing_execution;
    echo 'Starting Healing Listener...';
    python healing_listener.py;
    exec bash"

# 7. Start Mininet (Requires Sudo)
echo "[*] Starting Mininet Topology..."
echo "    (You may be asked for your sudo password)"
cd mininet_topology
sudo python3 topo_healing.py
