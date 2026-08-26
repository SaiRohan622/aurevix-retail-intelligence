"""
AUREVIX Backward-Compatibility Config Module
"""
from src.config.settings import settings, ProductionSettings, EnvironmentConfigError

__all__ = ["settings", "ProductionSettings", "EnvironmentConfigError"]
