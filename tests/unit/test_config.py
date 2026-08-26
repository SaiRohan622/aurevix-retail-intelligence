"""
AUREVIX — Unit Tests for Production Configuration Management
"""

import os
import pytest
from src.config.settings import ProductionSettings, EnvironmentConfigError


def test_default_development_config():
    cfg = ProductionSettings()
    assert cfg.ENV in ["development", "testing", "production"]
    assert cfg.WATERMARK_DELAY_MINUTES == 10
    assert cfg.POSTGRES_PORT == 5432
    assert cfg.SLA_MAX_LATENCY_MINUTES == 60


def test_production_password_validation(monkeypatch):
    monkeypatch.setenv("AUREVIX_ENV", "production")
    monkeypatch.setenv("POSTGRES_PASSWORD", "aurevix_secure_password_change_me")
    with pytest.raises(EnvironmentConfigError, match="Default password detected"):
        ProductionSettings()


def test_database_url_generation():
    cfg = ProductionSettings()
    db_url = cfg.get_database_url()
    assert "postgresql://" in db_url
    assert f":{cfg.POSTGRES_PORT}/" in db_url
