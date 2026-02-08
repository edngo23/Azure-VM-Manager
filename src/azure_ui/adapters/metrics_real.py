# Real Azure metrics adapter (stub for future migration)

from typing import Dict, List, Tuple, Optional
from datetime import datetime


class MetricsReal:
    """Real Azure Monitor metrics using Azure SDK."""
    
    def __init__(self):
        """Initialize with Azure credentials and clients."""
        # TODO: Initialize Azure SDK clients
        # from azure.identity import DefaultAzureCredential
        # from azure.monitor.query import MetricsQueryClient, AggregationType
        # credential = DefaultAzureCredential()
        # self.metrics_client = MetricsQueryClient(credential)
        pass
    
    def query_vm_metrics(
        self,
        subscription_id: str,
        resource_group: str,
        vm_name: str,
        minutes: Optional[int] = 15,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, List[Tuple[datetime, float]]]:
        """
        Query real metrics from Azure Monitor.
        Returns: {"Percentage CPU": [(timestamp, value), ...], "Network In Total": [...], "Network Out Total": [...]}
        """
        # TODO: Implement real Azure call
        # resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}"
        # metrics = self.metrics_client.query_resource(resource_id, ["Percentage CPU", "Network In Total", "Network Out Total"])
        raise NotImplementedError("Real Azure integration not yet implemented")
    
    def list_activity_events(
        self,
        subscription_id: str,
        resource_group: str,
        vm_name: str,
        start: datetime,
        end: datetime
    ) -> List[Tuple[datetime, str]]:
        """
        List activity events from Azure Activity Log.
        Returns: [(timestamp, operation), ...]
        """
        # TODO: Implement real Azure call
        # Use activity log API to retrieve start/deallocate events
        raise NotImplementedError("Real Azure integration not yet implemented")
    
    def total_runtime_in_window(
        self,
        subscription_id: str,
        resource_group: str,
        vm_name: str,
        start: datetime,
        end: datetime
    ) -> int:
        """
        Calculate total runtime from activity log.
        """
        # TODO: Implement by pairing start/deallocate events from activity log
        raise NotImplementedError("Real Azure integration not yet implemented")


# Global instance
_metrics_real_instance: Optional[MetricsReal] = None


def get_metrics_real() -> MetricsReal:
    """Get the metrics real instance."""
    global _metrics_real_instance
    if _metrics_real_instance is None:
        _metrics_real_instance = MetricsReal()
    return _metrics_real_instance
