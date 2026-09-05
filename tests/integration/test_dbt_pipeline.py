"""
AUREVIX — Integration Test for dbt-postgres Transformation Project
"""

import sys
import subprocess
import shutil
from pathlib import Path


def test_dbt_project_parse_and_compile():
    """Verify that dbt project parses all staging, intermediate, and mart models."""
    dbt_bin = shutil.which("dbt")
    if not dbt_bin:
        exe_name = "dbt.exe" if sys.platform == "win32" else "dbt"
        candidate = Path(sys.executable).parent / exe_name
        dbt_bin = str(candidate) if candidate.exists() else "dbt"
    cmd = [dbt_bin, "parse", "--project-dir", "dbt_aurevix", "--profiles-dir", "dbt_aurevix"]
    res = subprocess.run(cmd, capture_output=True, text=True)

    assert res.returncode == 0, f"dbt parse failed: {res.stderr or res.stdout}"
