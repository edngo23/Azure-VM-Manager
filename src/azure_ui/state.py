# State persistence module for runtime, snooze, and UI state

import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import json


class StateManager:
    """Manages persistent state across sessions."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.config_dir = self.project_root / "configs" / "local"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.runtime_state_file = self.config_dir / "runtime_state.yaml"
        self.sim_state_file = self.config_dir / "sim_state.yaml"
        self.runtime_state: Dict[str, Any] = {}
        self.sim_state: Dict[str, Any] = {}
        
        self._load_runtime_state()
        self._load_sim_state()
    
    def _load_runtime_state(self):
        """Load runtime state (start times, snoozes)."""
        if self.runtime_state_file.exists():
            try:
                with open(self.runtime_state_file) as f:
                    data = yaml.safe_load(f) or {}
                self.runtime_state = data
            except Exception as e:
                print(f"Warning: Failed to load runtime_state.yaml: {e}")
                self.runtime_state = {}
        else:
            self.runtime_state = {
                "runtime_start_times": {},
                "auto_shutdown_snoozed_until": {}
            }
    
    def _load_sim_state(self):
        """Load simulation state."""
        if self.sim_state_file.exists():
            try:
                with open(self.sim_state_file) as f:
                    data = yaml.safe_load(f) or {}
                self.sim_state = data
            except Exception as e:
                print(f"Warning: Failed to load sim_state.yaml: {e}")
                self.sim_state = {}
        else:
            self.sim_state = {"vms": {}}
    
    def _save_runtime_state(self):
        """Persist runtime state."""
        try:
            with open(self.runtime_state_file, "w") as f:
                yaml.dump(self.runtime_state, f, default_flow_style=False)
        except Exception as e:
            print(f"Warning: Failed to save runtime_state.yaml: {e}")
    
    def _save_sim_state(self):
        """Persist simulation state."""
        try:
            with open(self.sim_state_file, "w") as f:
                yaml.dump(self.sim_state, f, default_flow_style=False)
        except Exception as e:
            print(f"Warning: Failed to save sim_state.yaml: {e}")
    
    # Runtime state accessors
    def get_runtime_start_time(self, vm_key: str) -> Optional[datetime]:
        """Get recorded start time for a VM."""
        times = self.runtime_state.get("runtime_start_times", {})
        if ts_str := times.get(vm_key):
            try:
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
    
    def set_runtime_start_time(self, vm_key: str, dt: Optional[datetime]):
        """Record or clear a VM's start time."""
        if "runtime_start_times" not in self.runtime_state:
            self.runtime_state["runtime_start_times"] = {}
        if dt:
            self.runtime_state["runtime_start_times"][vm_key] = dt.isoformat()
        else:
            self.runtime_state["runtime_start_times"].pop(vm_key, None)
        self._save_runtime_state()
    
    def get_snooze_until(self, vm_key: str) -> Optional[datetime]:
        """Get snooze deadline for a VM."""
        snoozed = self.runtime_state.get("auto_shutdown_snoozed_until", {})
        if ts_str := snoozed.get(vm_key):
            try:
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
    
    def set_snooze_until(self, vm_key: str, dt: Optional[datetime]):
        """Set or clear snooze deadline for a VM."""
        if "auto_shutdown_snoozed_until" not in self.runtime_state:
            self.runtime_state["auto_shutdown_snoozed_until"] = {}
        if dt:
            self.runtime_state["auto_shutdown_snoozed_until"][vm_key] = dt.isoformat()
        else:
            self.runtime_state["auto_shutdown_snoozed_until"].pop(vm_key, None)
        self._save_runtime_state()
    
    # Simulation state accessors
    def get_vm_sim_state(self, vm_key: str) -> Dict[str, Any]:
        """Get simulation state for a VM."""
        if "vms" not in self.sim_state:
            self.sim_state["vms"] = {}
        
        if vm_key not in self.sim_state["vms"]:
            # Initialize new VM state
            import hashlib
            seed = int(hashlib.md5(vm_key.encode()).hexdigest(), 16) % (2**31)
            self.sim_state["vms"][vm_key] = {
                "power_state": "PowerState/deallocated",
                "last_start_utc": None,
                "last_stop_utc": None,
                "seed": seed,
                "history": [],
                "pending_op": None,
                "pending_op_at": None
            }
            self._save_sim_state()
        
        return self.sim_state["vms"][vm_key]
    
    def set_vm_sim_state(self, vm_key: str, state: Dict[str, Any]):
        """Update simulation state for a VM."""
        if "vms" not in self.sim_state:
            self.sim_state["vms"] = {}
        self.sim_state["vms"][vm_key] = state
        self._save_sim_state()
    
    def clear_all(self):
        """Clear all state (for testing)."""
        self.runtime_state = {
            "runtime_start_times": {},
            "auto_shutdown_snoozed_until": {}
        }
        self.sim_state = {"vms": {}}
        self._save_runtime_state()
        self._save_sim_state()


# Global state manager instance
_state_manager_instance: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get the global state manager (singleton)."""
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
    return _state_manager_instance
