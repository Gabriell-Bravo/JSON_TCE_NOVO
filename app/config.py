from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = DATA_DIR / "exports"
DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-secret-change-me")
_raw_db_url = os.getenv("APP_DATABASE_URL", f"sqlite:///{DATA_DIR / 'delib361.db'}")
DATABASE_URL = _raw_db_url.replace("postgres://", "postgresql://", 1) if _raw_db_url.startswith("postgres://") else _raw_db_url
ADMIN_USER = os.getenv("APP_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("APP_ADMIN_PASSWORD", "Admin@12345")
FORCE_SECURE_COOKIE = os.getenv("APP_FORCE_SECURE_COOKIE", "false").lower() == "true"
# Limite de importação de planilhas (MB). O e-TCERJ aceita JSON de remessa até ~40 MB.
MAX_UPLOAD_SIZE = int(os.getenv("APP_MAX_UPLOAD_MB", "25")) * 1024 * 1024
