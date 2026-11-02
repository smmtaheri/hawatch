"""Script tests must find sibling utilities regardless of pytest's cwd."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
