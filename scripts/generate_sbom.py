"""
AUREVIX — Software Bill of Materials (SBOM) Generator (CycloneDX 1.5 JSON)
Generates an audit-ready, machine-readable Software Bill of Materials for AUREVIX dependencies.
"""

import sys
import json
import uuid
import datetime
from pathlib import Path
from importlib import metadata

OUTPUT_PATH = Path("sbom.json")


def generate_cyclonedx_sbom(output_file: Path = OUTPUT_PATH) -> dict:
    """Generates CycloneDX 1.5 standard JSON SBOM from the active environment."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    serial_number = f"urn:uuid:{uuid.uuid4()}"

    components = []
    licenses_count = {}

    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata.get("Name", "").lower()):
        meta = dist.metadata
        pkg_name = meta.get("Name")
        if not pkg_name:
            continue
        version = meta.get("Version", "unknown")
        summary = meta.get("Summary", "")
        license_name = meta.get("License", "Unknown") or "Unknown"

        # Tally license for summary
        short_license = license_name.split("\n")[0][:40]
        licenses_count[short_license] = licenses_count.get(short_license, 0) + 1

        component = {
            "type": "library",
            "bom-ref": f"pkg:pypi/{pkg_name}@{version}",
            "name": pkg_name,
            "version": version,
            "description": summary,
            "scope": "required",
            "licenses": [{"license": {"name": short_license}}],
            "purl": f"pkg:pypi/{pkg_name}@{version}"
        }
        components.append(component)

    sbom_doc = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": serial_number,
        "version": 1,
        "metadata": {
            "timestamp": now_iso,
            "tools": [
                {
                    "vendor": "AUREVIX Security",
                    "name": "aurevix-sbom-generator",
                    "version": "1.0.0"
                }
            ],
            "component": {
                "type": "application",
                "name": "AUREVIX Universal Business Analytics Platform",
                "version": "2.1.0",
                "description": "Enterprise-grade Lakehouse BI, Streaming & Analytics Engine"
            }
        },
        "components": components
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sbom_doc, f, indent=2, ensure_ascii=False)

    print(f"SBOM successfully generated: {output_file.resolve()}")
    print(f"Total components cataloged: {len(components)}")
    print("License Distribution (Top 5):")
    for lic, count in sorted(licenses_count.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  - {lic}: {count} packages")

    return sbom_doc


if __name__ == "__main__":
    generate_cyclonedx_sbom()
