"""Pytest fixtures: каждый тест получает чистую SQLite-базу в памяти."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def fresh_db(monkeypatch):
    """Configure an in-memory SQLite engine for each test."""
    import db as db_module

    test_url = "sqlite:///:memory:"
    monkeypatch.setenv("DATABASE_URL", test_url)
    monkeypatch.setattr(db_module, "DATABASE_URL", test_url)
    db_module.reset_engine()
    db_module.init_db(test_url)
    yield db_module
    db_module.reset_engine()


@pytest.fixture()
def pg_db(monkeypatch):
    """Optional integration fixture against the docker-compose Postgres.

    Skipped automatically if no Postgres is reachable at TEST_DATABASE_URL.
    """
    import sqlalchemy
    import db as db_module

    url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://incomelab:incomelab@localhost:5432/incomelab",
    )
    try:
        engine = sqlalchemy.create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
    except Exception as e:  # pragma: no cover - environmental
        pytest.skip(f"PostgreSQL не доступен по {url}: {e}")

    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db_module, "DATABASE_URL", url)
    db_module.reset_engine()
    db_module.init_db(url)
    db_module.delete_all_entries()
    yield db_module
    db_module.delete_all_entries()
    db_module.reset_engine()
