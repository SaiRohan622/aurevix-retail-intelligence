"""
AUREVIX — Unit Tests for Platform Health & Readiness Probes
"""

from src.common.health import PlatformHealthChecker


def test_platform_liveness_probe():
    checker = PlatformHealthChecker()
    res = checker.check_liveness()
    assert res["status"] == "UP"
    assert "python_version" in res["runtime"]


def test_storage_lakehouse_health():
    checker = PlatformHealthChecker()
    res = checker.check_storage_lakehouse()
    assert res["status"] == "HEALTHY"
    assert res["gold_ready"] is True
    assert res["silver_ready"] is True
    assert res["bronze_ready"] is True


def test_readiness_probe_structure():
    checker = PlatformHealthChecker()
    res = checker.check_readiness()
    assert "ready" in res
    assert "status" in res
    assert "components" in res
    assert res["ready"] is True
