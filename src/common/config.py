"""
config.py — Centralised credential and configuration loader
============================================================
Loads secrets from secrets/.env via python-dotenv.
Exposes:
  - OPENAI_API_KEY   (default: "ollama" — works with local Ollama)
  - LLM_API_BASE     (default: "http://localhost:11434/v1" — local Ollama)
  - LLM_MODEL        (default: "llama3.1:8b")
  - JSL_LICENSE_PATH (absolute path to jsl_license.json)
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate project root and secrets/.env
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parents[1]
_ENV_FILE = _PROJECT_ROOT / "secrets" / ".env"

# Load .env if present (won't overwrite existing env vars already set)
try:
    from dotenv import load_dotenv
    if _ENV_FILE.exists():
        load_dotenv(dotenv_path=_ENV_FILE, override=False)
except ImportError:
    pass  # python-dotenv not installed; rely on env vars set externally

# ---------------------------------------------------------------------------
# Expose config values with Ollama-friendly defaults
# ---------------------------------------------------------------------------

OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "ollama")
LLM_API_BASE: str = os.environ.get("LLM_API_BASE", "http://localhost:11434/v1")
LLM_MODEL: str = os.environ.get("LLM_MODEL", "llama3.1:8b")

_jsl_raw = os.environ.get("JSL_LICENSE_PATH", "secrets/jsl_license.json")
if _jsl_raw:
    _jsl_path = Path(_jsl_raw)
    if not _jsl_path.is_absolute():
        _jsl_path = _PROJECT_ROOT / _jsl_path
    JSL_LICENSE_PATH: str = str(_jsl_path)
else:
    JSL_LICENSE_PATH = ""
