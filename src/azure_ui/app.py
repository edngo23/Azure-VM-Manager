"""
Azure VM Manager - Streamlit Application

A web application for managing Azure Virtual Machines including:
- Starting and stopping VMs
- Monitoring CPU and network metrics
- Viewing runtime statistics
- Auto-shutdown with snooze functionality
"""

import sys
from pathlib import Path

# Add src directory to path so imports work when run with streamlit
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Optional

from azure_ui.config import get_config
from azure_ui.state import get_state_manager
from azure_ui.azure_client import get_azure_client
from azure_ui.metrics import get_metrics_client
from azure_ui.utils import StateUtils, FormatUtils, CacheManager


# Configuration
PAGE_CONFIG = {
    "page_title": "Azure VM Manager",
    "page_icon": "☁️",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}


def init_page():
    """Initialize page configuration and session state."""
    st.set_page_config(**PAGE_CONFIG)
    StateUtils.init_session_state()


def load_ui_prefs():
    """Load UI preferences from config."""
    cfg = get_config()
    st.session_state["inactivity_monitor_enabled"] = cfg.get_ui_pref("inactivity_monitor_enabled", False)
    st.session_state["monitor_window_minutes"] = cfg.get_ui_pref("monitor_window_minutes", 5)
    st.session_state["cpu_threshold"] = cfg.get_ui_pref("cpu_threshold", 5.0)
    st.session_state["net_threshold_mb"] = cfg.get_ui_pref("net_threshold_mb", 10.0)
    st.session_state["metrics_window_choice"] = cfg.get_ui_pref("metrics_window_choice", "current")
    st.session_state["ui_prefs_loaded"] = True


def render_sidebar():
    """Render sidebar with controls and settings."""
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Metrics window selection
        st.subheader("Metrics Display")
        metrics_window = st.selectbox(
            "Metrics Window",
            options=["current", "1d", "7d", "30d", "90d"],
            format_func=StateUtils.get_window_label,
            key="metrics_window_choice"
        )
        
        # Auto-shutdown settings
        st.subheader("Auto-Shutdown Monitor")
        inactivity_enabled = st.checkbox(
            "Enable Inactivity Monitor",
            key="inactivity_monitor_enabled"
        )
        
        if inactivity_enabled:
            st.slider(
                "Monitor Window (minutes)",
                min_value=1,
                max_value=60,
                value=st.session_state.get("monitor_window_minutes", 5),
                key="monitor_window_minutes"
            )
            
            st.slider(
                "CPU Threshold (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.get("cpu_threshold", 5.0),
                step=0.5,
                key="cpu_threshold"
            )
            
            st.slider(
                "Network Threshold (MB)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.get("net_threshold_mb", 10.0),
                step=0.5,
                key="net_threshold_mb"
            )
        
        # Simulation diagnostics
        st.subheader("Diagnostics")
        diagnostics_shown = st.session_state.get("show_diagnostics", False)
        button_text = "🔍 Hide Simulation State" if diagnostics_shown else "🔍 Show Simulation State"
        
        if st.button(button_text):
            st.session_state["show_diagnostics"] = not st.session_state.get("show_diagnostics", False)
            st.rerun()
        
        if st.session_state.get("show_diagnostics"):
            render_diagnostics()


def render_diagnostics():
    """Render simulation diagnostics panel."""
    st.markdown("---")
    st.markdown("### Simulation Diagnostics")
    
    cfg = get_config()
    state_mgr = get_state_manager()
    client = get_azure_client()
    
    st.write(f"**Simulation Mode:** {client.sim_mode}")
    st.write(f"**VMs Loaded:** {len(cfg.get_vms())}")
    
    for vm in cfg.get_vms():
        vm_key = vm.get_key()
        vm_state = state_mgr.get_vm_sim_state(vm_key)
        power_state = vm_state.get("power_state", "Unknown")
        
        with st.expander(f"📊 {vm.name}"):
            st.write(f"**Key:** `{vm_key}`")
            st.write(f"**Power State:** {power_state}")
            st.write(f"**Seed:** {vm_state.get('seed')}")
            st.write(f"**Last Start UTC:** {vm_state.get('last_start_utc', 'None')}")
            st.write(f"**Last Stop UTC:** {vm_state.get('last_stop_utc', 'None')}")
            st.write(f"**Pending Op:** {vm_state.get('pending_op', 'None')}")
            
            if history := vm_state.get("history"):
                st.write(f"**History ({len(history)} events):**")
                for event in history[-5:]:  # Show last 5
                    st.write(f"  - {event['type'].upper()} at {event['at']}")


def render_vm_card(vm, azure_client, metrics_client, state_mgr):
    """Render a single VM control card."""
    vm_key = vm.get_key()
    
    # Get current state
    power_state = azure_client.get_vm_power_state(vm.subscription_id, vm.resource_group, vm.name)
    running_since = azure_client.get_vm_running_since(vm.subscription_id, vm.resource_group, vm.name)
    
    # Sync vm_ops with actual pending operations
    # If transition is complete, clear the vm_ops entry
    is_transitioning = "starting" in power_state.lower() or "deallocating" in power_state.lower()
    if vm_key in st.session_state["vm_ops"] and not is_transitioning:
        del st.session_state["vm_ops"][vm_key]
    
    # Track VMs with current runs for auto-refresh optimization
    if running_since and "running" in power_state.lower():
        if "vms_with_current_runs" not in st.session_state:
            st.session_state["vms_with_current_runs"] = set()
        st.session_state["vms_with_current_runs"].add(vm_key)
    else:
        if "vms_with_current_runs" in st.session_state:
            st.session_state["vms_with_current_runs"].discard(vm_key)
    
    with st.container():
        # Header with VM name and status badge
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            badge = FormatUtils.get_power_state_badge_color(power_state)
            label = FormatUtils.get_power_state_label(power_state)
            st.markdown(f"### {badge} {vm.name}")
        
        with col2:
            st.caption(f"RG: {vm.resource_group}")
        
        with col3:
            st.caption(label)
        
        # Runtime display - shows runtime in selected metrics window
        window_choice = st.session_state.get("metrics_window_choice", "current")
        
        if window_choice == "current":
            # For "current run" window, show only the live uptime if running
            if running_since and "running" in power_state.lower():
                uptime_seconds = int((datetime.now(timezone.utc) - running_since).total_seconds())
                uptime_str = FormatUtils.format_uptime(uptime_seconds)
                st.metric("Runtime", uptime_str)
            else:
                st.metric("Runtime", "—")
        else:
            # For other windows, show total runtime in that window
            minutes = StateUtils.get_metrics_window_minutes(window_choice)
            if minutes:
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(minutes=minutes)
                total_runtime_secs = metrics_client.total_runtime_in_window(
                    vm.subscription_id, vm.resource_group, vm.name, start_time, end_time
                )
                runtime_str = FormatUtils.format_uptime(total_runtime_secs)
                st.metric("Runtime", runtime_str)
            else:
                st.metric("Runtime", "—")
        
        # Control buttons
        col_start, col_stop = st.columns(2)
        
        is_running = "running" in power_state.lower()
        is_transitioning = "starting" in power_state.lower() or "deallocating" in power_state.lower()
        
        with col_start:
            if st.button(
                "▶️ Start" if not is_running else "✓ Running",
                disabled=is_running or is_transitioning,
                key=f"start_{vm_key}"
            ):
                azure_client.begin_start_vm(vm.subscription_id, vm.resource_group, vm.name)
                st.session_state["vm_ops"][vm_key] = "starting"
                st.rerun()
        
        with col_stop:
            if st.button(
                "⏹️ Stop",
                disabled=not is_running or is_transitioning,
                key=f"stop_{vm_key}"
            ):
                # Show confirmation modal
                st.session_state["manual_shutdown_confirm"][vm_key] = True
                st.rerun()
        
        # Metrics charts
        if st.session_state.get("metrics_window_choice"):
            render_metrics(vm, metrics_client)
        
        # Statistics
        render_statistics(vm, metrics_client, state_mgr)


def render_metrics(vm, metrics_client):
    """Render metrics charts for a VM."""
    window_choice = st.session_state.get("metrics_window_choice", "current")
    minutes = StateUtils.get_metrics_window_minutes(window_choice)
    
    try:
        # Query metrics
        metrics_data = metrics_client.query_vm_metrics(
            vm.subscription_id,
            vm.resource_group,
            vm.name,
            minutes=minutes
        )
        
        if metrics_data and metrics_data.get("Percentage CPU"):
            st.markdown("#### Metrics")
            
            # Get data
            cpu_data = metrics_data.get("Percentage CPU", [])
            net_in_data = metrics_data.get("Network In Total", [])
            net_out_data = metrics_data.get("Network Out Total", [])
            
            if cpu_data:
                # CPU chart - format timestamps concisely
                cpu_dict = {
                    "Time": [_format_timestamp_concise(t) for t, _ in cpu_data],
                    "CPU %": [v for _, v in cpu_data]
                }
                cpu_df = pd.DataFrame(cpu_dict)
                st.markdown("<h3 style='text-align: center'>CPU Utilization</h3>", unsafe_allow_html=True)
                st.line_chart(data=cpu_df, x="Time", y="CPU %", use_container_width=True)
            
            if net_in_data:
                # Network chart - convert bytes to MB and format timestamps
                net_dict = {
                    "Time": [_format_timestamp_concise(t) for t, _ in net_in_data],
                    "Network In (MB)": [v / (1024 * 1024) for _, v in net_in_data],
                    "Network Out (MB)": [v / (1024 * 1024) for _, v in net_out_data] if net_out_data else [0] * len(net_in_data)
                }
                net_df = pd.DataFrame(net_dict)
                st.markdown("<h3 style='text-align: center'>Network I/O</h3>", unsafe_allow_html=True)
                st.line_chart(data=net_df, x="Time", y=["Network In (MB)", "Network Out (MB)"], use_container_width=True)
    
    except Exception as e:
        st.error(f"Failed to load metrics: {str(e)}")


def _format_timestamp_concise(dt: datetime) -> str:
    """Format datetime concisely for chart readability.
    
    Uses HH:MM format if within last 24 hours, MM-DD HH:MM otherwise.
    """
    now = datetime.now(timezone.utc)
    
    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Check if within 24 hours
    if (now - dt).total_seconds() < 86400:
        return dt.strftime("%H:%M")
    else:
        return dt.strftime("%m-%d %H:%M")



def render_statistics(vm, metrics_client, state_mgr):
    """Render VM statistics."""
    try:
        # Get runtime stats
        now = datetime.now(timezone.utc)
        days_back = 90
        start_window = now - timedelta(days=days_back)
        
        total_runtime = metrics_client.total_runtime_in_window(
            vm.subscription_id,
            vm.resource_group,
            vm.name,
            start_window,
            now
        )
        
        st.caption(f"Runtime (last {days_back}d): {FormatUtils.format_uptime(total_runtime)}")
    
    except Exception as e:
        st.caption(f"Stats unavailable: {str(e)}")


def render_shutdown_confirmation(vm_key: str, azure_client, state_mgr):
    """Render shutdown confirmation modal."""
    if st.session_state.get("manual_shutdown_confirm", {}).get(vm_key):
        with st.container():
            st.warning("⚠️ Are you sure you want to stop this VM?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✓ Yes, Stop Now", key=f"confirm_stop_{vm_key}"):
                    cfg = get_config()
                    vm = next((v for v in cfg.get_vms() if v.get_key() == vm_key), None)
                    if vm:
                        azure_client.begin_deallocate_vm(vm.subscription_id, vm.resource_group, vm.name)
                        st.session_state["manual_shutdown_confirm"][vm_key] = False
                        st.rerun()
            
            with col2:
                if st.button("✗ Cancel", key=f"cancel_stop_{vm_key}"):
                    st.session_state["manual_shutdown_confirm"][vm_key] = False
                    st.rerun()


def main():
    """Main application entry point."""
    init_page()
    
    # Load preferences on first run
    if not st.session_state.get("ui_prefs_loaded"):
        load_ui_prefs()
    
    # Render UI
    st.title("☁️ Azure VM Manager")
    st.markdown("Manage your Azure Virtual Machines from this control panel.")
    
    # Sidebar
    render_sidebar()
    
    # Main content
    cfg = get_config()
    azure_client = get_azure_client()
    metrics_client = get_metrics_client()
    state_mgr = get_state_manager()
    
    vms = cfg.get_vms()
    
    if not vms:
        st.warning("⚠️ No VMs configured. Please set AZURE_VMS_JSON or configure azure_vms.yaml")
        st.stop()
    
    # Render VM cards
    st.markdown("### Virtual Machines")
    
    for vm in vms:
        vm_key = vm.get_key()
        
        # Render shutdown confirmation if needed
        render_shutdown_confirmation(vm_key, azure_client, state_mgr)
        
        # Render VM card
        render_vm_card(vm, azure_client, metrics_client, state_mgr)
    
    # Auto-refresh logic:
    # - Refresh if there are transitioning VMs (starting/deallocating)
    # - Refresh if there are VMs with current runs (looking at live runtime)
    # - Otherwise, only refresh on user actions (button clicks, settings changes)
    has_transitioning_vms = bool(st.session_state.get("vm_ops"))
    has_current_runs = bool(st.session_state.get("vms_with_current_runs"))
    
    if has_transitioning_vms or has_current_runs:
        if has_transitioning_vms:
            st.info("VMs are transitioning. Page will auto-refresh...")
        st.rerun()


if __name__ == "__main__":
    main()
