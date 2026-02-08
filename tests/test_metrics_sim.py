# Unit tests for metrics simulator

import pytest
from datetime import datetime, timezone, timedelta
from src.azure_ui.adapters.metrics_sim import MetricsSimulator
from src.azure_ui.adapters.compute_sim import ComputeSimulator
from src.azure_ui.state import StateManager
import time


@pytest.fixture
def simulator():
    """Create a fresh simulator for each test."""
    state_mgr = StateManager()
    state_mgr.clear_all()
    return MetricsSimulator()


@pytest.fixture
def compute_sim():
    """Create compute simulator for full workflow tests."""
    return ComputeSimulator()


def test_query_vm_metrics(simulator):
    """Test querying metrics returns all three metric types."""
    metrics = simulator.query_vm_metrics("sub1", "rg1", "vm1", minutes=15)
    
    assert "Percentage CPU" in metrics
    assert "Network In Total" in metrics
    assert "Network Out Total" in metrics
    
    # Should have data points
    assert len(metrics["Percentage CPU"]) > 0
    assert len(metrics["Network In Total"]) > 0
    assert len(metrics["Network Out Total"]) > 0


def test_metrics_cpu_values_valid(simulator):
    """Test that CPU values are within valid range."""
    metrics = simulator.query_vm_metrics("sub1", "rg1", "vm1", minutes=15)
    cpu_data = metrics["Percentage CPU"]
    
    for timestamp, value in cpu_data:
        assert 0 <= value <= 100, f"CPU value {value} out of range [0, 100]"


def test_metrics_network_non_negative(simulator):
    """Test that network values are non-negative."""
    metrics = simulator.query_vm_metrics("sub1", "rg1", "vm1", minutes=15)
    
    for timestamp, value in metrics["Network In Total"]:
        assert value >= 0, f"Network In value {value} is negative"
    
    for timestamp, value in metrics["Network Out Total"]:
        assert value >= 0, f"Network Out value {value} is negative"


def test_list_activity_events_empty(simulator):
    """Test listing events from an untouched VM."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=1)
    
    events = simulator.list_activity_events("sub1", "rg1", "vm1", start, now)
    
    # Should be empty for uninitialized VM
    assert len(events) == 0


def test_list_activity_events_after_start(simulator, compute_sim):
    """Test listing events after starting a VM."""
    # Start a VM
    compute_sim.begin_start_vm("sub1", "rg1", "vm1")
    
    # Wait for completion
    for _ in range(20):
        if compute_sim.get_vm_power_state("sub1", "rg1", "vm1") == "PowerState/running":
            break
        time.sleep(0.5)
    
    # Query events
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=1)
    events = simulator.list_activity_events("sub1", "rg1", "vm1", start, now)
    
    # Should have at least a start event
    assert len(events) >= 1
    assert "start" in events[0][1]


def test_total_runtime_in_window(simulator, compute_sim):
    """Test calculating total runtime."""
    # Start a VM
    compute_sim.begin_start_vm("sub1", "rg1", "vm1")
    
    # Wait for completion
    for _ in range(20):
        if compute_sim.get_vm_power_state("sub1", "rg1", "vm1") == "PowerState/running":
            break
        time.sleep(0.5)
    
    # Query runtime
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=1)
    runtime = simulator.total_runtime_in_window("sub1", "rg1", "vm1", start, now)
    
    # Should have some runtime
    assert runtime > 0


def test_total_runtime_90_day_clamp(simulator):
    """Test that 90-day clamp is applied."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=120)  # 120 days back
    
    # Should not raise, should clamp internally
    runtime = simulator.total_runtime_in_window("sub1", "rg1", "vm1", start, now)
    assert isinstance(runtime, int)
    assert runtime >= 0
