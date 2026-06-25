from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = DATA_DIR / "exports"
DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-secret-change-me")
DATABASE_URL = os.getenv("APP_DATABASE_URL", f"sqlite:///{DATA_DIR / 'delib361.db'}")
ADMIN_USER = os.getenv("APP_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("APP_ADMIN_PASSWORD", "Admin@12345")
FORCE_SECURE_COOKIE = os.getenv("APP_FORCE_SECURE_COOKIE", "false").lower() == "true"
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
