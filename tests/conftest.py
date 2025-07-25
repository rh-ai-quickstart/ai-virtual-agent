"""Pytest configuration for the AI-Virtual-Agent repo.

Ensures the repository root is always at the beginning of 'sys.path', so
that 'import backend' (and other top-level packages) succeed even when
pytest is invoked from a sub-directory.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
