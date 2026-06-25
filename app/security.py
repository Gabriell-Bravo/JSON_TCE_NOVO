from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from typing import Iterable

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from .models import AuditLog, User

PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256$%d$%s$%s" % (
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode(),
        base64.b64encode(dk).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        alg, iterations, salt_b64, hash_b64 = stored.split("$", 3)
        if alg != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def get_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def validate_csrf(request: Request, csrf_token: str | None) -> None:
    expected = request.session.get("csrf_token")
    if not expected or not csrf_token or not hmac.compare_digest(str(expected), str(csrf_token)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF inválido.")


def require_login(request: Request, db: Session) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


def require_role(user: User, roles: Iterable[str]) -> None:
    allowed = set(roles)
    if user.role not in allowed and user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Perfil sem permissão para esta operação.")


def audit(db: Session, request: Request, user: User | None, action: str, entity: str, entity_id: int | None = None, details: str | None = None) -> None:
    ip = request.client.host if request.client else None
    db.add(AuditLog(user_id=user.id if user else None, action=action, entity=entity, entity_id=entity_id, details=details, ip=ip))
    db.commit()
