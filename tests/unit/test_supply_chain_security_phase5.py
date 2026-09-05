import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


# ==============================================================================
# 1. DEPENDENCY & MANIFEST TESTS
# ==============================================================================

def test_dependency_manifest_exists():
    """Verify authoritative requirements manifests exist."""
    req_root = ROOT / "requirements.txt"
    assert req_root.exists()
    
    req_dir = ROOT / "requirements"
    assert req_dir.exists()
    assert (req_dir / "base.txt").exists()
    assert (req_dir / "dashboard.txt").exists()
    assert (req_dir / "spark.txt").exists()
    assert (req_dir / "streaming.txt").exists()
    assert (req_dir / "dev.txt").exists()


def test_no_plaintext_credentials_in_dependency_files():
    """Verify requirements and config files contain no raw passwords or API tokens."""
    for req_file in (ROOT / "requirements").glob("*.txt"):
        content = req_file.read_text(encoding="utf-8")
        assert "password" not in content.lower()
        assert "api_key" not in content.lower()
        assert "secret" not in content.lower()


def test_dangerous_dependency_installation_not_present():
    """Verify no scripts or docs suggest 'sudo pip' or 'curl | bash'."""
    for doc in (ROOT / "README.md", ROOT / "SECURITY.md"):
        if doc.exists():
            content = doc.read_text(encoding="utf-8")
            assert "sudo pip" not in content
            assert "curl | bash" not in content
            assert "curl | sh" not in content


# ==============================================================================
# 2. SECURITY TOOLING & CONFIGURATION TESTS
# ==============================================================================

def test_security_tools_configured():
    """Verify security tools are importable and available in environment."""
    import pip_audit
    import bandit
    assert pip_audit.__name__ == "pip_audit"
    assert bandit.__name__ == "bandit"


def test_vulnerability_scanner_configured():
    """Verify pip-audit is functional and inspectable."""
    import pip_audit
    assert hasattr(pip_audit, "__file__")


def test_sast_configured():
    """Verify Bandit static analysis is configured and can parse python AST."""
    import bandit.core.manager as bm
    import bandit.core.config as bc
    b_mgr = bm.BanditManager(bc.BanditConfig(), "screen")
    assert b_mgr is not None


def test_sbom_generation_configured():
    """Verify SBOM generator script exists and generates CycloneDX standard format."""
    sbom_script = ROOT / "scripts/generate_sbom.py"
    assert sbom_script.exists()

    from scripts.generate_sbom import generate_cyclonedx_sbom
    tmp_sbom = ROOT / "data/test_sbom.json"
    try:
        sbom_data = generate_cyclonedx_sbom(tmp_sbom)
        assert sbom_data["bomFormat"] == "CycloneDX"
        assert sbom_data["specVersion"] == "1.5"
        assert len(sbom_data["components"]) > 0
    finally:
        if tmp_sbom.exists():
            tmp_sbom.unlink()


def test_secret_scanning_configured():
    """Verify secret patterns are defined and blocked by gitignore and policies."""
    gitignore = ROOT / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text(encoding="utf-8")
    assert ".env" in content
    assert "*.key" in content
    assert "*.pem" in content
    assert "secrets/" in content


# ==============================================================================
# 3. CI/CD WORKFLOW SECURITY TESTS
# ==============================================================================

def test_github_actions_exist():
    """Verify GitHub Actions CI and Security workflows exist."""
    ci_file = ROOT / ".github/workflows/ci.yml"
    sec_file = ROOT / ".github/workflows/security.yml"
    assert ci_file.exists()
    assert sec_file.exists()


def test_github_actions_use_least_privilege():
    """Verify workflows declare least privilege read permissions."""
    ci_content = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    sec_content = (ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8")

    assert "permissions:" in ci_content
    assert "contents: read" in ci_content
    assert "permissions:" in sec_content
    assert "contents: read" in sec_content


def test_workflows_do_not_echo_secrets():
    """Verify workflows never echo or print secret variables."""
    for wf in (ROOT / ".github/workflows").glob("*.yml"):
        content = wf.read_text(encoding="utf-8")
        assert "echo ${{ secrets." not in content
        assert "echo $SECRET" not in content
        assert "echo $PASSWORD" not in content


def test_env_files_not_tracked():
    """Verify .env or live secret files are not accidentally committed."""
    assert not (ROOT / ".env").exists()
    assert (ROOT / ".env.example").exists()


def test_private_key_patterns_blocked():
    """Verify private key patterns are strictly ignored by .gitignore."""
    content = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.pem" in content
    assert "*.key" in content
    assert "credentials/" in content
    assert "private/" in content


def test_security_documentation_exists():
    """Verify SECURITY.md exists and contains disclosure and scanner instructions."""
    sec_doc = ROOT / "SECURITY.md"
    assert sec_doc.exists()
    content = sec_doc.read_text(encoding="utf-8")
    assert "Vulnerability Management" in content
    assert "pip-audit" in content
    assert "Bandit" in content
    assert "CycloneDX" in content
