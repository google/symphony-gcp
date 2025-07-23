import sys
from pathlib import Path

# ensure that modules are properly imported from the "src" directory and "tests" directory
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
