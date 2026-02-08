# Metrics simulation adapter

import random
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional
from azure_ui.state import get_state_manager


class MetricsSimulator:
    """Simulates Azure Monitor metrics for VMs."""
    
    def __init__(self):
        self.state_mgr = get_state_manager()
    
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
        Query synthetic metrics for a VM.
        Returns: {"Percentage CPU": [(timestamp, value), ...], "Network In Total": [...], "Network Out Total": [...]}
        """
        vm_key = self._get_vm_key(subscription_id, resource_group, vm_name)
        vm_state = self.state_mgr.get_vm_sim_state(vm_key)
        
        # Determine time window
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            if minutes:
                start_time = end_time - timedelta(minutes=minutes)
            else:
                start_time = end_time - timedelta(minutes=15)
        
        # Clamp to 90 days
        max_lookback = end_time - timedelta(days=89, hours=23, minutes=59, seconds=59)
        if start_time < max_lookback:
            start_time = max_lookback
        
        # Determine interval
        span_minutes = (end_time - start_time).total_seconds() / 60
        if span_minutes > 1440:  # > 1 day
            interval_seconds = 900  # 15 minutes
        elif span_minutes > 360:  # > 6 hours
            interval_seconds = 300  # 5 minutes
        else:
            interval_seconds = 60  # 1 minute
        
        # Generate synthetic data
        seed = vm_state.get("seed", 12345)
        rng = np.random.default_rng(seed)
        py_rng = random.Random(seed)
        
        # Get start events from history
        history = vm_state.get("history", [])
        start_events = []
        for h in history:
            try:
                event_str = h["at"]
                # Handle both formats: with timezone or with Z suffix
                if event_str.endswith("Z"):
                    dt = datetime.fromisoformat(event_str[:-1] + "+00:00")
                else:
                    dt = datetime.fromisoformat(event_str)
                start_events.append(dt)
            except (ValueError, KeyError):
                pass
        
        # Build time series
        cpu_series = []
        net_in_series = []
        net_out_series = []
        
        current = start_time
        while current <= end_time:
            # Base metrics (idle)
            cpu_base = max(0, min(100, rng.normal(2.0, 0.8)))
            net_in_base = max(0, rng.normal(150_000, 50_000))
            net_out_base = max(0, rng.normal(150_000, 50_000))
            
            # Add peaks from recent starts
            cpu_peak = 0
            net_peak_in = 0
            net_peak_out = 0
            
            for start_event in start_events:
                if start_event <= current:
                    minutes_since = (current - start_event).total_seconds() / 60
                    if minutes_since < 10:  # Peak contribution within 10 minutes of start
                        amplitude = py_rng.uniform(40, 80)
                        tau = py_rng.uniform(2, 6)  # minutes
                        cpu_peak += amplitude * np.exp(-minutes_since / tau)
                        
                        net_amplitude = py_rng.uniform(2e6, 20e6)
                        net_tau = py_rng.uniform(2, 8)  # minutes
                        net_peak_in += net_amplitude * np.exp(-minutes_since / net_tau)
                        net_peak_out += net_amplitude * np.exp(-minutes_since / net_tau)
            
            # Combine
            cpu_value = max(0, min(100, cpu_base + cpu_peak))
            net_in_value = max(0, net_in_base + net_peak_in)
            net_out_value = max(0, net_out_base + net_peak_out)
            
            cpu_series.append((current, cpu_value))
            net_in_series.append((current, net_in_value))
            net_out_series.append((current, net_out_value))
            
            current += timedelta(seconds=interval_seconds)
        
        return {
            "Percentage CPU": cpu_series,
            "Network In Total": net_in_series,
            "Network Out Total": net_out_series
        }
    
    def list_activity_events(
        self,
        subscription_id: str,
        resource_group: str,
        vm_name: str,
        start: datetime,
        end: datetime
    ) -> List[Tuple[datetime, str]]:
        """
        List activity events (start/deallocate) for a VM in time range.
        Returns: [(timestamp, operation), ...]
        """
        vm_key = self._get_vm_key(subscription_id, resource_group, vm_name)
        vm_state = self.state_mgr.get_vm_sim_state(vm_key)
        
        # Clamp to 90 days
        max_lookback = end - timedelta(days=89, hours=23, minutes=59, seconds=59)
        if start < max_lookback:
            start = max_lookback
        
        history = vm_state.get("history", [])
        events = []
        
        for item in history:
            try:
                event_time_str = item["at"]
                # Handle both formats: with timezone or with Z suffix
                if event_time_str.endswith("Z"):
                    event_time = datetime.fromisoformat(event_time_str[:-1] + "+00:00")
                else:
                    event_time = datetime.fromisoformat(event_time_str)
                
                if start <= event_time <= end:
                    op_type = item["type"]
                    op_name = f"Microsoft.Compute/virtualMachines/{op_type}"
                    events.append((event_time, op_name))
            except (ValueError, KeyError):
                pass
        
        # Sort by timestamp
        events.sort(key=lambda x: x[0])
        return events
    
    def total_runtime_in_window(
        self,
        subscription_id: str,
        resource_group: str,
        vm_name: str,
        start: datetime,
        end: datetime
    ) -> int:
        """
        Calculate total runtime (in seconds) within a time window.
        Handles starts before window, deallocates after window, and incomplete segments.
        """
        vm_key = self._get_vm_key(subscription_id, resource_group, vm_name)
        vm_state = self.state_mgr.get_vm_sim_state(vm_key)
        
        # Clamp to 90 days
        max_lookback = end - timedelta(days=89, hours=23, minutes=59, seconds=59)
        if start < max_lookback:
            start = max_lookback
        
        history = vm_state.get("history", [])
        total_seconds = 0
        
        # Parse history into (start_time, stop_time) pairs
        segments = []
        segment_start = None
        
        for item in history:
            event_time = datetime.fromisoformat(item["at"].replace("Z", "+00:00"))
            if item["type"] == "start":
                segment_start = event_time
            elif item["type"] == "deallocate" and segment_start:
                segments.append((segment_start, event_time))
                segment_start = None
        
        # Handle open segment (running but not yet deallocated)
        if segment_start:
            current_state = vm_state.get("power_state", "PowerState/deallocated")
            if current_state == "PowerState/running":
                segments.append((segment_start, datetime.now(timezone.utc)))
        
        # Intersect segments with query window
        for seg_start, seg_end in segments:
            # Clamp segment to window
            clamp_start = max(seg_start, start)
            clamp_end = min(seg_end, end)
            
            if clamp_start < clamp_end:
                total_seconds += int((clamp_end - clamp_start).total_seconds())
        
        return total_seconds
    
    @staticmethod
    def _get_vm_key(subscription_id: str, resource_group: str, vm_name: str) -> str:
        """Create unique VM key."""
        return f"{subscription_id}/{resource_group}/{vm_name}"


# Global instance
_metrics_sim_instance: Optional[MetricsSimulator] = None


def get_metrics_simulator() -> MetricsSimulator:
    """Get the metrics simulator instance."""
    global _metrics_sim_instance
    if _metrics_sim_instance is None:
        _metrics_sim_instance = MetricsSimulator()
    return _metrics_sim_instance
