# Azure client module - branching between real and simulation modes

import os
from typing import Optional
from datetime import datetime


class AzureClient:
    """Unified Azure client that branches between real and simulation modes."""
    
    def __init__(self):
        self.sim_mode = self._is_sim_mode()
        
        if self.sim_mode:
            from adapters.compute_sim import get_compute_simulator
            self.compute = get_compute_simulator()
        else:
            from adapters.compute_real import get_compute_real
            self.compute = get_compute_real()
    
    @staticmethod
    def _is_sim_mode() -> bool:
        """Check if simulation mode is enabled."""
        sim_mode = os.getenv("AZURE_SIM_MODE", "1").lower()
        return sim_mode in ("1", "true", "yes", "on")
    
    def get_vm_power_state(self, subscription_id: str, resource_group: str, vm_name: str) -> str:
        """Get VM power state."""
        return self.compute.get_vm_power_state(subscription_id, resource_group, vm_name)
    
    def begin_start_vm(self, subscription_id: str, resource_group: str, vm_name: str):
        """Start a VM."""
        self.compute.begin_start_vm(subscription_id, resource_group, vm_name)
    
    def begin_deallocate_vm(self, subscription_id: str, resource_group: str, vm_name: str):
        """Deallocate a VM."""
        self.compute.begin_deallocate_vm(subscription_id, resource_group, vm_name)
    
    def get_vm_running_since(self, subscription_id: str, resource_group: str, vm_name: str) -> Optional[datetime]:
        """Get VM last start time."""
        return self.compute.get_vm_running_since(subscription_id, resource_group, vm_name)


# Global instance
_azure_client_instance: Optional[AzureClient] = None


def get_azure_client() -> AzureClient:
    """Get the Azure client instance."""
    global _azure_client_instance
    if _azure_client_instance is None:
        _azure_client_instance = AzureClient()
    return _azure_client_instance
