# Metrics module - branching between real and simulation modes

import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class MetricsClient:
    """Unified Metrics client that branches between real and simulation modes."""
    
    def __init__(self):
        self.sim_mode = self._is_sim_mode()
        
        if self.sim_mode:
            from adapters.metrics_sim import get_metrics_simulator
            self.monitor = get_metrics_simulator()
        else:
            from adapters.metrics_real import get_metrics_real
            self.monitor = get_metrics_real()
    
    @staticmethod
    def _is_sim_mode() -> bool:
        """Check if simulation mode is enabled."""
        sim_mode = os.getenv("AZURE_SIM_MODE", "1").lower()
        return sim_mode in ("1", "true", "yes", "on")
    
    def query_vm_metrics(
        self,
        subscription_id: str,
        resource_group: str,
        vm_name: str,
        minutes: Optional[int] = 15,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, List[Tuple[datetime, float]]]:
        """Query VM metrics."""
        return self.monitor.query_vm_metrics(
            subscription_id, resource_group, vm_name, minutes, start_time, end_time
        )
    
    def list_activity_events(
        self,
        subscription_id: str,
        resource_group: str,
        vm_name: str,
        start: datetime,
        end: datetime
    ) -> List[Tuple[datetime, str]]:
        """List activity events."""
        return self.monitor.list_activity_events(
            subscription_id, resource_group, vm_name, start, end
        )
    
    def total_runtime_in_window(
        self,
        subscription_id: str,
        resource_group: str,
        vm_name: str,
        start: datetime,
        end: datetime
    ) -> int:
        """Get total runtime in window."""
        return self.monitor.total_runtime_in_window(
            subscription_id, resource_group, vm_name, start, end
        )


# Global instance
_metrics_client_instance: Optional[MetricsClient] = None


def get_metrics_client() -> MetricsClient:
    """Get the metrics client instance."""
    global _metrics_client_instance
    if _metrics_client_instance is None:
        _metrics_client_instance = MetricsClient()
    return _metrics_client_instance
