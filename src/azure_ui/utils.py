# Utilities for caching, formatting, and state management

import streamlit as st
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from typing import Dict, List, Tuple, Optional, Any


class CacheManager:
    """Manages metrics caching with TTL support."""
    
    CACHE_TTL_METRICS_LIVE = 30  # seconds
    CACHE_TTL_METRICS_WINDOW = 60  # seconds
    CACHE_TTL_RUNTIME = 60  # seconds
    CACHE_TTL_LAST_START = 300  # seconds
    
    @staticmethod
    def get_or_fetch_metrics(
        vm_key: str,
        minutes: int,
        fetch_func
    ) -> Dict[str, List[Tuple[datetime, float]]]:
        """Get cached metrics or fetch fresh if expired."""
        cache_key = f"metrics_{vm_key}_{minutes}"
        now = datetime.now(timezone.utc)
        
        if cache_key in st.session_state:
            cached_at, data = st.session_state[cache_key]
            if (now - cached_at).total_seconds() < CacheManager.CACHE_TTL_METRICS_LIVE:
                return data
        
        # Fetch fresh
        data = fetch_func()
        st.session_state[cache_key] = (now, data)
        return data
    
    @staticmethod
    def get_or_fetch_runtime(
        vm_key: str,
        start: datetime,
        end: datetime,
        fetch_func
    ) -> int:
        """Get cached runtime or fetch fresh if expired."""
        cache_key = f"runtime_{vm_key}_{start.isoformat()}_{end.isoformat()}"
        now = datetime.now(timezone.utc)
        
        if cache_key in st.session_state:
            cached_at, data = st.session_state[cache_key]
            if (now - cached_at).total_seconds() < CacheManager.CACHE_TTL_RUNTIME:
                return data
        
        # Fetch fresh
        data = fetch_func()
        st.session_state[cache_key] = (now, data)
        return data
    
    @staticmethod
    def clear_metrics_cache():
        """Clear all metrics caches."""
        keys_to_delete = [k for k in st.session_state.keys() if k.startswith("metrics_")]
        for k in keys_to_delete:
            del st.session_state[k]


class FormatUtils:
    """Formatting utilities for display."""
    
    @staticmethod
    def format_uptime(seconds: int) -> str:
        """Format seconds as human-readable uptime."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}m {secs}s"
        elif seconds < 86400:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours}h {mins}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"
    
    @staticmethod
    def format_datetime(dt: Optional[datetime]) -> str:
        """Format datetime for display."""
        if dt is None:
            return "—"
        # Convert to local if aware, otherwise assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt.astimezone()
        return local_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def format_bytes(bytes_val: float) -> str:
        """Format bytes as human-readable."""
        units = ["B", "KB", "MB", "GB"]
        for unit in units:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} TB"
    
    @staticmethod
    def get_power_state_badge_color(state: str) -> str:
        """Get badge color for power state."""
        state_lower = state.lower()
        if "running" in state_lower:
            return "🟢"
        elif "deallocated" in state_lower:
            return "⚪"
        elif "starting" in state_lower:
            return "🟡"
        elif "deallocating" in state_lower:
            return "🟠"
        else:
            return "⚫"
    
    @staticmethod
    def get_power_state_label(state: str) -> str:
        """Get friendly label for power state."""
        state_lower = state.lower()
        if "running" in state_lower:
            return "Running"
        elif "deallocated" in state_lower:
            return "Stopped"
        elif "starting" in state_lower:
            return "Starting..."
        elif "deallocating" in state_lower:
            return "Stopping..."
        else:
            return "Unknown"


class StateUtils:
    """Session state utilities."""
    
    @staticmethod
    def init_session_state():
        """Initialize session state if not already done."""
        defaults = {
            "vm_ops": {},  # {vm_name: "starting"|"deallocating"}
            "auto_shutdown_pending": {},  # {vm_key: {"deadline": datetime, "reason": str}}
            "auto_shutdown_snoozed_until": {},  # {vm_key: datetime}
            "manual_shutdown_confirm": {},  # {vm_key: True}
            "snooze_modal": None,  # {"vm": vm_key, "until": iso_str} | None
            "metrics_window_choice": "current",  # "current", "1d", "7d", "30d", "90d"
            "ui_prefs_loaded": False,
            "pending_ui_sync": {},
            "sidebar_notice": None,
            "metrics_cache_epoch": 0
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    @staticmethod
    def get_metrics_window_minutes(choice: str) -> Optional[int]:
        """Get minutes for a metrics window choice."""
        windows = {
            "current": None,  # Special case: use last_start_utc
            "1d": 1440,
            "7d": 10080,
            "30d": 43200,
            "90d": 129600
        }
        return windows.get(choice)
    
    @staticmethod
    def get_window_label(choice: str) -> str:
        """Get friendly label for window choice."""
        labels = {
            "current": "Current Run",
            "1d": "Last 24 Hours",
            "7d": "Last 7 Days",
            "30d": "Last 30 Days",
            "90d": "Last 90 Days"
        }
        return labels.get(choice, "Unknown")
