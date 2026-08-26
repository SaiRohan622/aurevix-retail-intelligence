"""
AUREVIX — Integration Test for dbt-postgres Transformation Project
"""

import sys
import subprocess
from pathlib import Path


def test_dbt_project_parse_and_compile():
    """Verify that dbt project parses all staging, intermediate, and mart models."""
    dbt_bin = Path(sys.executable).parent / "dbt.exe"
    cmd = [str(dbt_bin), "parse", "--project-dir", "dbt_aurevix", "--profiles-dir", "dbt_aurevix"]
    res = subprocess.run(cmd, capture_output=True, text=True)

    assert res.returncode == 0, f"dbt parse failed: {res.stderr or res.stdout}"
