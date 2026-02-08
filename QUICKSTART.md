# Azure VM Manager - Quick Reference

## 🚀 Getting Started (60 seconds)

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app (uses default demo VM)
streamlit run src/azure_ui/app.py

# 3. Open browser to http://localhost:8501
```

## 🎮 Using the App

| Action | Steps |
|--------|-------|
| **Start VM** | Click ▶️ Start → Transitions: Starting (yellow) → Running (green) |
| **Stop VM** | Click ⏹️ Stop → Confirm → Transitions: Deallocating (orange) → Stopped (white) |
| **View Metrics** | Select window in sidebar → Charts update (CPU %, Network In/Out) |
| **Check Diagnostics** | Sidebar → 🔍 Show Simulation State → Expand any VM |

## 📋 Configuration

### Quick Config (Environment Variable)
```powershell
$env:AZURE_VMS_JSON='{"vms":[{"name":"vm1","resource_group":"rg","subscription_id":"sub"}]}'
streamlit run src/azure_ui/app.py
```

### File Config (Recommended)
1. Copy template: `copy configs\local\azure_vms.example.yaml configs\local\azure_vms.yaml`
2. Edit with your VMs
3. Run app

## 📁 Key Files

| File | Purpose |
|------|---------|
| `src/azure_ui/app.py` | Main Streamlit UI |
| `src/azure_ui/config.py` | Load VMs and preferences |
| `src/azure_ui/state.py` | Save/load persistent state |
| `src/azure_ui/adapters/compute_sim.py` | VM state machine simulation |
| `src/azure_ui/adapters/metrics_sim.py` | Synthetic metrics |
| `configs/local/sim_state.yaml` | VM states and history (auto-created) |
| `configs/local/runtime_state.yaml` | Start times, snoozes (auto-created) |

## 🧪 Testing

```powershell
pip install pytest
pytest tests/ -v
```

## 🔧 Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `AZURE_SIM_MODE` | `1` (default) | Use simulation (no Azure needed) |
| `AZURE_SIM_MODE` | `0` | Use real Azure (requires setup) |
| `AZURE_VMS_JSON` | `{"vms":[...]}` | Define VMs inline |

## 📊 Simulation Features

- **Realistic Delays**: Start 8-15s, Stop 5-12s
- **Synthetic Metrics**: CPU, Network In/Out with realistic patterns
- **Deterministic**: Same VM always generates same metrics (seeded RNG)
- **State Persisted**: All changes saved to `sim_state.yaml`
- **90-Day History**: Activity logs and runtime tracking

## 🔄 Switching to Real Azure

1. Implement real adapters in `adapters/compute_real.py` and `metrics_real.py`
2. Set `AZURE_SIM_MODE=0`
3. Configure Azure credentials (Managed Identity or Service Principal)
4. UI remains **unchanged**

## 🎯 VM State Machine

```
Deallocated
    ↓ Click Start
Starting (8-15s)
    ↓ After delay
Running
    ↓ Click Stop
Deallocating (5-12s)
    ↓ After delay
Deallocated
```

## 📈 Metrics Windows

| Selection | Time Range | Data Points |
|-----------|-----------|-------------|
| Current Run | From last start | Updated live |
| 1d | Last 24 hours | 288 points (5m intervals) |
| 7d | Last 7 days | 672 points (15m intervals) |
| 30d | Last 30 days | 2880 points (15m intervals) |
| 90d | Last 90 days | 8640 points (15m intervals) |

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| No VMs appear | Set `AZURE_VMS_JSON` or create `configs/local/azure_vms.yaml` |
| Metrics blank | Start a VM first (green badge required) |
| State not saving | Check `configs/local/` is writable |
| Tests fail | Run `pytest tests/ -v` to see errors |

## 💡 Tips

- **Demo Mode**: Just run the app with no config for a demo VM
- **Inspect State**: Click 🔍 in sidebar to see simulation state
- **Reproducible**: Same VM always generates same metrics (for testing)
- **No Credentials**: Simulation mode never needs Azure secrets
- **Portable**: Works offline, zero external dependencies (except Python packages)

## 📚 Documentation

- **README.md** - Full usage guide
- **IMPLEMENTATION_GUIDE.md** - Detailed architecture
- **Project Description and Framework.txt** - Original spec

---

**Version**: 1.0.0  
**Status**: Complete & Ready to Use  
**Mode**: Simulation (set AZURE_SIM_MODE=0 for real Azure)
