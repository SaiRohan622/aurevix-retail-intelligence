"""
AUREVIX — Platform Health Check CLI Script
Executes liveness and readiness diagnostic checks and exits with appropriate return codes.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.common.health import PlatformHealthChecker


def main():
    checker = PlatformHealthChecker()
    res = checker.check_readiness()
    print(json.dumps(res, indent=2))

    if res.get("ready"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
