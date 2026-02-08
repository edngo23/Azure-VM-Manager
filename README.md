# Azure VM Manager

A **Streamlit-based web application** for managing Azure Virtual Machines. This replica operates in simulation mode by default (no real Azure resources contacted) but is designed to support real Azure integration when needed.

## Features

- ✅ **VM Control**: Start and stop virtual machines with confirmation dialogs
- ✅ **Real-time Metrics**: CPU usage, network in/out traffic with interactive charts
- ✅ **Runtime Tracking**: Monitor total uptime across multiple time windows (current run, 1d, 7d, 30d, 90d)
- ✅ **Simulation Mode**: Full functionality without Azure resources; deterministic and reproducible
- ✅ **Persistent State**: VM states, snooze settings, and UI preferences saved to YAML configs
- ✅ **Auto-shutdown Monitor** (ready to implement): Inactivity detection with snooze functionality
- ✅ **Responsive UI**: Single-page Streamlit app with sidebar controls

## Project Structure

```
Azure-VM-Manager/
├── src/azure_ui/
│   ├── app.py                  # Main Streamlit application
│   ├── config.py               # Configuration management (VMs, preferences)
│   ├── state.py                # Persistent state management
│   ├── azure_client.py         # Azure compute API (branches real/sim)
│   ├── metrics.py              # Azure metrics API (branches real/sim)
│   ├── utils.py                # Utilities (caching, formatting, session state)
│   └── adapters/
│       ├── compute_sim.py      # Compute simulation (state machine, transitions)
│       ├── metrics_sim.py       # Metrics simulation (synthetic data generation)
│       ├── compute_real.py     # Real Azure compute (stub for migration)
│       └── metrics_real.py     # Real Azure metrics (stub for migration)
├── configs/local/
│   ├── azure_vms.yaml          # VM inventory (auto-created from env or example)
│   ├── ui_prefs.yaml           # UI preferences (auto-created from defaults)
│   ├── runtime_state.yaml      # Runtime state: start times, snoozes (auto-created)
│   └── sim_state.yaml          # Simulation state: VM states, history (auto-created)
├── tests/
│   ├── test_compute_sim.py     # Unit tests for compute simulator
│   └── test_metrics_sim.py     # Unit tests for metrics simulator
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## Getting Started

### 1. Install Dependencies

```bash
cd Azure-VM-Manager
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure VMs

Choose **ONE** configuration method:

#### Option A: Environment Variable (JSON)

```bash
set AZURE_VMS_JSON={"vms":[{"name":"vm-1","resource_group":"rg-1","subscription_id":"sub-1"}]}
```

#### Option B: YAML File (Recommended for local dev)

Create `configs/local/azure_vms.yaml`:

```yaml
vms:
  - name: demo-vm-1
    resource_group: demo-rg
    subscription_id: demo-sub-1
  - name: demo-vm-2
    resource_group: demo-rg
    subscription_id: demo-sub-1
```

### 3. Run the Application

```bash
streamlit run src/azure_ui/app.py
```

The app opens at `http://localhost:8501`

## Usage

### Starting a VM
1. Click **▶️ Start** button on any VM card
2. VM transitions to "Starting..." (yellow badge)
3. After 8-15 seconds, transitions to "Running" (green badge)
4. Metrics begin generating synthetic data

### Stopping a VM
1. Click **⏹️ Stop** button
2. Confirmation dialog appears
3. Click **Yes, Stop Now** to confirm
4. VM transitions to "Stopping..." (orange badge)
5. After 5-12 seconds, transitions to "Stopped" (white badge)

### Viewing Metrics
- Select **Metrics Window** in sidebar: "Current Run", "Last 24h", "Last 7d", etc.
- Charts update to show CPU % and Network traffic
- Data is synthetic but deterministic

### Simulation Diagnostics
1. Click **🔍 Show Simulation State** in sidebar
2. Expand each VM to see power state, timings, and event history

## Simulation Behavior

### Compute State Machine

```
Deallocated → Starting (8-15s) → Running → Deallocating (5-12s) → Deallocated
```

### Synthetic Metrics

- **Baseline**: Idle CPU ~2%, Network In/Out ~150KB
- **Start Peak**: CPU spikes 40-80% for 2-6 minutes, Network 2-20MB, then exponential decay
- **Clamping**: CPU capped at [0, 100]%, Network always ≥0

## Configuration & State Files

### `azure_vms.yaml` - VM Inventory
Define all VMs here (copied from template)

### `ui_prefs.yaml` - User Preferences
Sidebar defaults (auto-created from code defaults)

### `sim_state.yaml` - Simulation State
VM states, history, RNG seeds (auto-created and persisted)

### `runtime_state.yaml` - Runtime State
Start times, snooze deadlines (auto-created and persisted)

## Migrating to Real Azure

When ready to use real Azure resources:

1. Implement real adapters in `src/azure_ui/adapters/compute_real.py` and `metrics_real.py`
2. Set credentials using Azure SDK
3. Set `AZURE_SIM_MODE=0` environment variable

The UI remains **completely unchanged** — adapters are swapped transparently.

## Testing

```bash
pytest tests/
```

Tests cover:
- ✅ VM power state transitions
- ✅ Start/deallocate operations and timing
- ✅ Metrics generation
- ✅ Runtime aggregation

## Troubleshooting

### No VMs appear

Ensure one of these:
1. `AZURE_VMS_JSON` environment variable is set
2. `configs/local/azure_vms.yaml` exists

### Metrics not updating

- Verify `AZURE_SIM_MODE=1` 
- Check that VM has been started (green badge)

---

**Happy VM managing! 🚀**
