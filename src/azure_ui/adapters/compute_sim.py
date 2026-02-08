# Compute simulation adapter

import random
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from azure_ui.state import get_state_manager


class ComputeSimulator:
    """Simulates Azure Compute operations (VMs)."""
    
    def __init__(self):
        self.state_mgr = get_state_manager()
    
    def get_vm_power_state(self, subscription_id: str, resource_group: str, vm_name: str) -> str:
        """
        Get current power state of a VM.
        Returns: "PowerState/deallocated", "PowerState/starting", "PowerState/running", "PowerState/deallocating"
        """
        vm_key = self._get_vm_key(subscription_id, resource_group, vm_name)
        vm_state = self.state_mgr.get_vm_sim_state(vm_key)
        
        # Check if pending operation should complete
        if vm_state.get("pending_op") and vm_state.get("pending_op_at"):
            pending_at_str = vm_state["pending_op_at"]
            # Handle both formats: "2026-02-07T22:21:27.872298+00:00" and "2026-02-07T22:21:27Z"
            if pending_at_str.endswith("Z"):
                pending_at = datetime.fromisoformat(pending_at_str[:-1] + "+00:00")
            else:
                pending_at = datetime.fromisoformat(pending_at_str)
            
            if datetime.now(timezone.utc) >= pending_at:
                # Transition complete
                op = vm_state["pending_op"]
                if op == "start":
                    vm_state["power_state"] = "PowerState/running"
                    vm_state["last_start_utc"] = datetime.now(timezone.utc).isoformat()
                    vm_state["history"].append({
                        "type": "start",
                        "at": vm_state["last_start_utc"]
                    })
                elif op == "deallocate":
                    vm_state["power_state"] = "PowerState/deallocated"
                    vm_state["last_stop_utc"] = datetime.now(timezone.utc).isoformat()
                    vm_state["history"].append({
                        "type": "deallocate",
                        "at": vm_state["last_stop_utc"]
                    })
                vm_state["pending_op"] = None
                vm_state["pending_op_at"] = None
                self.state_mgr.set_vm_sim_state(vm_key, vm_state)
        
        return vm_state.get("power_state", "PowerState/deallocated")
    
    def begin_start_vm(self, subscription_id: str, resource_group: str, vm_name: str):
        """Start a VM (async operation)."""
        vm_key = self._get_vm_key(subscription_id, resource_group, vm_name)
        vm_state = self.state_mgr.get_vm_sim_state(vm_key)
        
        # Transition to "starting"
        vm_state["power_state"] = "PowerState/starting"
        
        # Set pending operation
        seed = vm_state.get("seed", 12345)
        rng = random.Random(seed)
        delay_seconds = rng.uniform(8, 15)  # 8-15 second start time
        pending_at = (datetime.now(timezone.utc) + timedelta(seconds=delay_seconds))
        vm_state["pending_op"] = "start"
        vm_state["pending_op_at"] = pending_at.isoformat()
        
        self.state_mgr.set_vm_sim_state(vm_key, vm_state)
    
    def begin_deallocate_vm(self, subscription_id: str, resource_group: str, vm_name: str):
        """Deallocate (stop) a VM (async operation)."""
        vm_key = self._get_vm_key(subscription_id, resource_group, vm_name)
        vm_state = self.state_mgr.get_vm_sim_state(vm_key)
        
        # Transition to "deallocating"
        vm_state["power_state"] = "PowerState/deallocating"
        
        # Set pending operation
        seed = vm_state.get("seed", 12345)
        rng = random.Random(seed)
        delay_seconds = rng.uniform(5, 12)  # 5-12 second stop time
        pending_at = (datetime.now(timezone.utc) + timedelta(seconds=delay_seconds))
        vm_state["pending_op"] = "deallocate"
        vm_state["pending_op_at"] = pending_at.isoformat()
        
        self.state_mgr.set_vm_sim_state(vm_key, vm_state)
    
    def get_vm_running_since(self, subscription_id: str, resource_group: str, vm_name: str) -> Optional[datetime]:
        """Get the timestamp when the VM was last started."""
        vm_key = self._get_vm_key(subscription_id, resource_group, vm_name)
        vm_state = self.state_mgr.get_vm_sim_state(vm_key)
        
        if last_start := vm_state.get("last_start_utc"):
            try:
                return datetime.fromisoformat(last_start.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
    
    @staticmethod
    def _get_vm_key(subscription_id: str, resource_group: str, vm_name: str) -> str:
        """Create unique VM key."""
        return f"{subscription_id}/{resource_group}/{vm_name}"


# Global instance
_compute_sim_instance: Optional[ComputeSimulator] = None


def get_compute_simulator() -> ComputeSimulator:
    """Get the compute simulator instance."""
    global _compute_sim_instance
    if _compute_sim_instance is None:
        _compute_sim_instance = ComputeSimulator()
    return _compute_sim_instance
