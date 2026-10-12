# AI Social Media Automation — Python engine
import sys
from pathlib import Path

# Ensure automation root is always on sys.path
_automation_root = str(Path(__file__).parent.resolve())
if _automation_root not in sys.path:
    sys.path.insert(0, _automation_root)
