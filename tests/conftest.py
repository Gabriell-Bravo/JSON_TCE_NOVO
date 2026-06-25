import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB = ROOT / "tests" / f".test_delib361_{os.getpid()}.db"
os.environ["APP_DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["APP_SECRET_KEY"] = "test-secret-key"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.main import app, init_db
from app.models import Programa, Secretaria, UnidadeGestora, User
from app.security import hash_password


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    init_db()
    yield
    engine.dispose()
    try:
        TEST_DB.unlink(missing_ok=True)
    except OSError:
        pass


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def secretaria_setup(db):
    s = db.scalar(select(Secretaria).where(Secretaria.sigla == "SMDS"))
    ug = db.scalar(select(UnidadeGestora).where(UnidadeGestora.secretaria_id == s.id))
    programa = db.scalar(select(Programa).where(Programa.secretaria_id == s.id))
    programa.codigo_etce = 100
    programa.homologado_etce = True
    programa.vigente = True
    db.commit()
    return s, ug, programa


def create_user(db, username: str, role: str, secretaria_id: int | None, password: str = "Senha@123") -> User:
    user = User(username=username, password_hash=hash_password(password), role=role, secretaria_id=secretaria_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(client: TestClient, username: str, password: str = "Senha@123") -> None:
    page = client.get("/login")
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert match
    client.post("/login", data={"username": username, "password": password, "csrf_token": match.group(1)}, follow_redirects=True)


def csrf_from(client: TestClient, url: str = "/") -> str:
    page = client.get(url)
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert match, f"CSRF não encontrado em {url}"
    return match.group(1)
