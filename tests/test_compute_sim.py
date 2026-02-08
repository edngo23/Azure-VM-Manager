# Unit tests for compute simulator

import pytest
from datetime import datetime, timezone, timedelta
from src.azure_ui.adapters.compute_sim import ComputeSimulator
from src.azure_ui.state import StateManager
import time


@pytest.fixture
def simulator():
    """Create a fresh simulator for each test."""
    # Clear state
    state_mgr = StateManager()
    state_mgr.clear_all()
    return ComputeSimulator()


def test_initial_power_state(simulator):
    """Test that VMs start deallocated."""
    state = simulator.get_vm_power_state("sub1", "rg1", "vm1")
    assert state == "PowerState/deallocated"


def test_begin_start_vm(simulator):
    """Test starting a VM transitions to starting state."""
    simulator.begin_start_vm("sub1", "rg1", "vm1")
    state = simulator.get_vm_power_state("sub1", "rg1", "vm1")
    assert state == "PowerState/starting"


def test_start_vm_completes(simulator):
    """Test that a starting VM eventually becomes running."""
    simulator.begin_start_vm("sub1", "rg1", "vm1")
    
    # Wait for transition
    for _ in range(20):
        state = simulator.get_vm_power_state("sub1", "rg1", "vm1")
        if state == "PowerState/running":
            break
        time.sleep(0.5)
    
    state = simulator.get_vm_power_state("sub1", "rg1", "vm1")
    assert state == "PowerState/running"


def test_get_vm_running_since(simulator):
    """Test getting the last start time."""
    simulator.begin_start_vm("sub1", "rg1", "vm1")
    before = datetime.now(timezone.utc)
    
    # Wait for completion
    for _ in range(20):
        state = simulator.get_vm_power_state("sub1", "rg1", "vm1")
        if state == "PowerState/running":
            break
        time.sleep(0.5)
    
    after = datetime.now(timezone.utc)
    running_since = simulator.get_vm_running_since("sub1", "rg1", "vm1")
    
    assert running_since is not None
    assert before <= running_since <= after


def test_deallocate_vm(simulator):
    """Test deallocating a running VM."""
    # Start first
    simulator.begin_start_vm("sub1", "rg1", "vm1")
    for _ in range(20):
        if simulator.get_vm_power_state("sub1", "rg1", "vm1") == "PowerState/running":
            break
        time.sleep(0.5)
    
    # Deallocate
    simulator.begin_deallocate_vm("sub1", "rg1", "vm1")
    state = simulator.get_vm_power_state("sub1", "rg1", "vm1")
    assert state == "PowerState/deallocating"
    
    # Wait for completion
    for _ in range(20):
        state = simulator.get_vm_power_state("sub1", "rg1", "vm1")
        if state == "PowerState/deallocated":
            break
        time.sleep(0.5)
    
    assert state == "PowerState/deallocated"
