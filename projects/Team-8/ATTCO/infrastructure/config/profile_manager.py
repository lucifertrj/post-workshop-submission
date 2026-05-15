"""
Runtime Profile Manager — orchestrates global profile resolution and distribution.
"""
from __future__ import annotations
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

class ProfileManager:
    """Manages ATTCO runtime profiles (research, balanced, aggressive, visualization)."""
    
    _config: Dict[str, Any] = {}
    _active_profile_name: str = "research"
    _active_profile_data: Dict[str, Any] = {}

    @classmethod
    def load(cls, profile_name: Optional[str] = None):
        """Loads the profile configuration and sets the active profile."""
        config_path = Path("config/runtime_profiles.yaml")
        if not config_path.exists():
            # Fallback for different execution contexts
            config_path = Path(__file__).parent.parent.parent / "config" / "runtime_profiles.yaml"
            
        if config_path.exists():
            with open(config_path, 'r') as f:
                cls._config = yaml.safe_load(f)
        else:
            logger.warning("profile_config_not_found", path=str(config_path))
            cls._config = {}

        # Resolution order: 1. Argument, 2. ENV, 3. Default
        resolved_name = profile_name or os.getenv("ATTCO_RUNTIME_PROFILE") or "research"
        
        if resolved_name not in cls._config:
            logger.warning("profile_not_found", requested=resolved_name, fallback="research")
            resolved_name = "research"
            
        cls._active_profile_name = resolved_name
        cls._active_profile_data = cls._config.get(resolved_name, {})
        
        logger.info("runtime_profile_activated", 
                    profile=resolved_name, 
                    description=cls._active_profile_data.get("description", "N/A"))

    @classmethod
    def get_active_profile_name(cls) -> str:
        return cls._active_profile_name

    @classmethod
    def get_active_profile(cls) -> Dict[str, Any]:
        if not cls._active_profile_data:
            cls.load()
        return cls._active_profile_data

    @classmethod
    def get_optimization_config(cls) -> Dict[str, Any]:
        return cls.get_active_profile().get("optimization", {})

    @classmethod
    def get_telemetry_config(cls) -> Dict[str, Any]:
        return cls.get_active_profile().get("telemetry", {})

    @classmethod
    def resolve_threshold(cls, key: str, default_value: Any) -> Any:
        """Helper to resolve a specific threshold from the active profile or fallback."""
        opt_config = cls.get_optimization_config()
        return opt_config.get(key, default_value)
