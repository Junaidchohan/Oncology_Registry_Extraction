"""
config.py — Centralised credential and configuration loader
============================================================
Loads secrets from secrets/.env via python-dotenv.
Exposes:
  - OPENAI_API_KEY
  - LLM_MODEL
  - JSL_LICENSE_PATH  (absolute path)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate project root and secrets/.env
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parents[1]
_ENV_FILE = _PROJECT_ROOT / "secrets" / ".env"

# Load .env if present (won't overwrite existing env vars)
try:
    from dotenv import load_dotenv
    if _ENV_FILE.exists():
        load_dotenv(dotenv_path=_ENV_FILE, override=False)
except ImportError:
    # python-dotenv not installed; rely on env vars being set manually
    pass

# ---------------------------------------------------------------------------
# Expose config values
# ---------------------------------------------------------------------------

OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
LLM_MODEL: str = os.environ.get("LLM_MODEL", "gpt-4o-mini")

_jsl_raw = os.environ.get("JSL_LICENSE_PATH", "")
if _jsl_raw:
    _jsl_path = Path(_jsl_raw)
    if not _jsl_path.is_absolute():
        _jsl_path = _PROJECT_ROOT / _jsl_path
    JSL_LICENSE_PATH: str = str(_jsl_path)
else:
    JSL_LICENSE_PATH = ""
