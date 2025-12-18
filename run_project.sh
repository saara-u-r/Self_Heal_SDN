#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status.

# --- CONFIGURATION: PATHS TO VIRTUAL ENVIRONMENTS ---

# 1. Environment for Ryu Controller
RYU_VENV="$HOME/Projects/self-heal-sdn/ryu_venv_38/bin/activate"

# 2. Environment for Telemetry Agent
AGENT_VENV="$HOME/Projects/self-heal-sdn/monitoring_and_telemetry/.venv/bin/activate"

# 3. Environment for ML Models
MODEL_DIR="$HOME/Projects/self-heal-sdn/model"
MODEL_VENV_DIR="$MODEL_DIR/.venv"
MODEL_PYTHON="$MODEL_VENV_DIR/bin/python3"
MARKER_FILE="$MODEL_VENV_DIR/installed"
# ----------------------------------------------------

# 1. Kill old processes
echo "[*] Cleaning up old processes..."
sudo mn -c
sudo fuser -k 6633/tcp || true
sudo fuser -k 8080/tcp || true
sudo fuser -k 8000/tcp || true
sudo killall python3 || true

# ----------------------------------------------------
# CHECK & SETUP ML ENVIRONMENT
# ----------------------------------------------------
echo "[*] Checking ML Environment..."

# Function to verify imports
verify_ml_env() {
    "$MODEL_PYTHON" -c "import tensorflow; import pandas; import numpy; import joblib; print('Imports OK')" >/dev/null 2>&1
}

# 1. Verification Check: if marker exists but imports fail, delete marker
if [ -f "$MARKER_FILE" ]; then
    if ! verify_ml_env; then
        echo "[-] ML Environment corrupted (imports failed). Reinstalling..."
        rm -f "$MARKER_FILE"
        rm -rf "$MODEL_VENV_DIR"
    fi
fi

if [ ! -f "$MARKER_FILE" ]; then
    echo "[*] Setting up ML Virtual Environment (First Run)..."
    echo "    This may take a few minutes."

    # Try to install system dependencies for h5py/tensorflow (Debian/Ubuntu)
    echo "[*] Attempting to install system dependencies (requires sudo)..."
    if command -v apt-get >/dev/null; then
        sudo apt-get update || true
        # Install hdf5 headers and pkg-config which are CRITICAL for h5py on ARM
        sudo apt-get install -y pkg-config libhdf5-dev python3-dev build-essential || echo "[-] Failed to install system deps. Continuing..."
    fi

    # Create Venv
    if [ ! -d "$MODEL_VENV_DIR" ]; then
        python3 -m venv "$MODEL_VENV_DIR"
    fi

    # Install Dependencies
    # Upgrading pip is crucial for wheels
    "$MODEL_PYTHON" -m pip install --upgrade pip setuptools wheel

    echo "[*] Installing Python packages..."
    # Build h5py specifically if needed, then others
    if ! "$MODEL_PYTHON" -m pip install tensorflow pandas scikit-learn joblib pyyaml; then
        echo "[-] Standard install failed. Retrying one-by-one..."
        "$MODEL_PYTHON" -m pip install --upgrade pip
        # Try installing h5py explicitly with pkg-config help if needed, but usually just pip install h5py works if sys deps are there
        "$MODEL_PYTHON" -m pip install h5py
        "$MODEL_PYTHON" -m pip install numpy pandas scikit-learn joblib pyyaml tensorflow
    fi
    
    # Final Verification
    if verify_ml_env; then
        touch "$MARKER_FILE"
        echo "[*] ML Environment Setup Complete."
    else
        echo "[!] CRITICAL: ML Environment setup failed. 'tensorflow/pandas' could not be imported."
        echo "    Please install dependencies manually using: source model/.venv/bin/activate && pip install tensorflow pandas"
        exit 1
    fi
else
    echo "[*] ML Environment found and verified."
fi

# CHECK & TRAIN MODELS
echo "[*] Checking Trained Models..."
if [ ! -f "$MODEL_DIR/lstmModels/lstm_final_model.h5" ] || [ ! -f "$MODEL_DIR/ifmodels/isolation_forest_model.pkl" ]; then
    echo "[*] Trained models not found. Starting Training..."
    
    # Train LSTM
    echo "    Training LSTM..."
    cd "$MODEL_DIR" || exit
    if ! "$MODEL_PYTHON" lstm_final.py; then
        echo "[!] LSTM Training Failed."
        exit 1
    fi
    
    # Train Isolation Forest
    echo "    Training Isolation Forest..."
    if ! "$MODEL_PYTHON" isolationForest.py; then
        echo "[!] Isolation Forest Training Failed."
        exit 1
    fi
    
    cd ..
    echo "[*] Training Complete."
else
    echo "[*] Models already trained."
fi

# ----------------------------------------------------

# 2. Start Ryu Controller
echo "[*] Starting Ryu Controller..."
gnome-terminal --tab --title="Controller" -- bash -c "source $RYU_VENV; cd controller_apps; ryu-manager sh_controller.py --verbose --ofp-tcp-listen-port 6633; exec bash"

# 3. Wait for Controller to initialize
sleep 5

# 4. Start Telemetry Agent
echo "[*] Starting Telemetry Agent..."
gnome-terminal --tab --title="Telemetry" -- bash -c "source $AGENT_VENV; cd monitoring_and_telemetry; python3 telemetry_agent.py; exec bash"

# 5. Start ML Pipeline
echo "[*] Starting Real-Time ML Pipeline..."
gnome-terminal --tab --title="ML Pipeline" -- bash -c "cd model; $MODEL_PYTHON run_realtime_pipeline.py; exec bash"

# 6. Start Mininet
echo "[*] Starting Mininet Topology..."
cd mininet_topology
sudo python3 topo_healing.py
