# Config module for loading VM inventory, preferences, and managing environment

import os
import json
import yaml
from typing import List, Dict, Optional, Any
from pathlib import Path
import base64


class VMConfig:
    """Represents a single VM configuration."""
    
    def __init__(self, name: str, resource_group: str, subscription_id: str):
        self.name = name
        self.resource_group = resource_group
        self.subscription_id = subscription_id
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "resource_group": self.resource_group,
            "subscription_id": self.subscription_id
        }
    
    @staticmethod
    def from_dict(d: Dict[str, str]) -> "VMConfig":
        return VMConfig(
            name=d.get("name", ""),
            resource_group=d.get("resource_group", ""),
            subscription_id=d.get("subscription_id", "")
        )
    
    def get_key(self) -> str:
        """Get unique identifier for this VM."""
        return f"{self.subscription_id}/{self.resource_group}/{self.name}"


class Config:
    """Centralized configuration management."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.config_dir = self.project_root / "configs" / "local"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.vms: List[VMConfig] = []
        self.ui_prefs: Dict[str, Any] = {}
        self._load_all()
    
    def _load_all(self):
        """Load VMs and UI preferences."""
        self._load_vms()
        self._load_ui_prefs()
    
    def _load_vms(self):
        """Load VM inventory from env, file, or defaults."""
        vms_list = []
        
        # Try AZURE_VMS_JSON env var
        if env_json := os.getenv("AZURE_VMS_JSON"):
            try:
                data = json.loads(env_json)
                vms_list = data.get("vms", [])
            except json.JSONDecodeError:
                print(f"Warning: AZURE_VMS_JSON invalid JSON")
        
        # Try AZURE_VMS_YAML_B64 env var
        elif env_yaml_b64 := os.getenv("AZURE_VMS_YAML_B64"):
            try:
                yaml_str = base64.b64decode(env_yaml_b64).decode("utf-8")
                data = yaml.safe_load(yaml_str)
                vms_list = data.get("vms", [])
            except Exception as e:
                print(f"Warning: AZURE_VMS_YAML_B64 decode failed: {e}")
        
        # Try local file
        elif (vm_file := self.config_dir / "azure_vms.yaml").exists():
            try:
                with open(vm_file) as f:
                    data = yaml.safe_load(f) or {}
                vms_list = data.get("vms", [])
            except Exception as e:
                print(f"Warning: Failed to load azure_vms.yaml: {e}")
        
        self.vms = [VMConfig.from_dict(vm) for vm in vms_list]
        
        # Ensure at least one default VM for demo
        if not self.vms:
            self.vms = [
                VMConfig(
                    name="demo-vm-1",
                    resource_group="demo-rg",
                    subscription_id="demo-sub"
                )
            ]
    
    def _load_ui_prefs(self):
        """Load UI preferences from file or defaults."""
        defaults = {
            "inactivity_monitor_enabled": False,
            "monitor_window_minutes": 5,
            "cpu_threshold": 5.0,
            "net_threshold_mb": 10.0,
            "metrics_window_choice": "current"
        }
        
        prefs_file = self.config_dir / "ui_prefs.yaml"
        if prefs_file.exists():
            try:
                with open(prefs_file) as f:
                    loaded = yaml.safe_load(f) or {}
                self.ui_prefs = {**defaults, **loaded}
            except Exception as e:
                print(f"Warning: Failed to load ui_prefs.yaml: {e}")
                self.ui_prefs = defaults
        else:
            self.ui_prefs = defaults
            self._save_ui_prefs()
    
    def _save_ui_prefs(self):
        """Save UI preferences to file."""
        prefs_file = self.config_dir / "ui_prefs.yaml"
        try:
            with open(prefs_file, "w") as f:
                yaml.dump(self.ui_prefs, f, default_flow_style=False)
        except Exception as e:
            print(f"Warning: Failed to save ui_prefs.yaml: {e}")
    
    def get_vms(self) -> List[VMConfig]:
        """Get all VMs."""
        return self.vms
    
    def get_ui_pref(self, key: str, default: Any = None) -> Any:
        """Get a UI preference."""
        return self.ui_prefs.get(key, default)
    
    def set_ui_pref(self, key: str, value: Any):
        """Set and persist a UI preference."""
        self.ui_prefs[key] = value
        self._save_ui_prefs()


# Global config instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get the global config instance (singleton)."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
