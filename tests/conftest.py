"""
FinOps Sentinel — Pytest Configuration
Shared fixtures and test configuration.
"""

import sys
from pathlib import Path

# Add project root to path so all imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
