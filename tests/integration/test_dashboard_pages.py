"""
AUREVIX — Integration Test for Streamlit Dashboard Application & Pages
"""
import importlib.util
from pathlib import Path


def test_dashboard_app_and_pages_syntax():
    base_dir = Path("dashboard")
    files_to_test = [base_dir / "app.py"] + list((base_dir / "pages").glob("*.py"))
    assert len(files_to_test) >= 10

    for fpath in files_to_test:
        spec = importlib.util.spec_from_file_location(fpath.stem, fpath)
        assert spec is not None, f"Failed to load spec for {fpath}"
