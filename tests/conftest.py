import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure PySpark workers use the exact isolated Python runtime (.venv Python 3.12)
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

# Hadoop winutils (Windows only)
hadoop_dir = PROJECT_ROOT / "infrastructure" / "hadoop"
if sys.platform == "win32" and hadoop_dir.exists():
    os.environ["HADOOP_HOME"] = str(hadoop_dir.resolve())
    os.environ["hadoop.home.dir"] = str(hadoop_dir.resolve())
    bin_dir = str((hadoop_dir / "bin").resolve())
    if bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
