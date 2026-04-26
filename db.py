"""Database layer for Income Lab.

Uses SQLAlchemy Core so the same code works with PostgreSQL (production,
via docker-compose) and SQLite (local dev / tests). The backend is selected
via the ``DATABASE_URL`` env var, e.g.::

    postgresql+psycopg2://incomelab:incomelab@localhost:5432/incomelab
    sqlite:///./data/income.db
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator, Optional

from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.sql import text

load_dotenv()

DEFAULT_SQLITE = f"sqlite:///{Path(__file__).parent / 'data' / 'income.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE)

metadata = MetaData()

entries_table = Table(
    "entries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("amount", Float, nullable=False),
    Column("currency", String(8), nullable=False, default="RUB"),
    Column("category", String(64), nullable=False, default="Зарплата"),
    Column("source", String(255), default=""),
    Column("note", String, default=""),
    Column("entry_date", Date, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Index("idx_entries_date", "entry_date"),
    Index("idx_entries_category", "category"),
)

goals_table = Table(
    "goals",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("title", String(255), nullable=False),
    Column("target", Float, nullable=False),
    Column("deadline", Date),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)


_engine: Optional[Engine] = None


def get_engine(url: Optional[str] = None) -> Engine:
    """Return (and lazily create) the SQLAlchemy engine."""
    global _engine
    target = url or DATABASE_URL
    if _engine is None or str(_engine.url) != target:
        kwargs = {"future": True, "pool_pre_ping": True}
        if target.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            db_path = target.replace("sqlite:///", "")
            if db_path and not db_path.startswith(":memory:"):
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(target, **kwargs)
    return _engine


def init_db(url: Optional[str] = None) -> None:
    engine = get_engine(url)
    metadata.create_all(engine)


def reset_engine() -> None:
    """Tests use this to drop the cached engine."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


@contextmanager
def get_conn() -> Iterator:
    engine = get_engine()
    with engine.begin() as conn:
        yield conn


def add_entry(
    amount: float,
    entry_date: date,
    category: str,
    source: str = "",
    note: str = "",
    currency: str = "RUB",
) -> int:
    if amount is None or float(amount) <= 0:
        raise ValueError("amount must be > 0")
    if not category:
        raise ValueError("category is required")
    with get_conn() as conn:
        result = conn.execute(
            insert(entries_table).values(
                amount=float(amount),
                currency=currency,
                category=category,
                source=source or "",
                note=note or "",
                entry_date=entry_date,
            )
        )
        return int(result.inserted_primary_key[0])


def update_entry(
    entry_id: int,
    amount: float,
    entry_date: date,
    category: str,
    source: str,
    note: str,
    currency: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            update(entries_table)
            .where(entries_table.c.id == entry_id)
            .values(
                amount=float(amount),
                currency=currency,
                category=category,
                source=source or "",
                note=note or "",
                entry_date=entry_date,
            )
        )


def delete_entry(entry_id: int) -> None:
    with get_conn() as conn:
        conn.execute(delete(entries_table).where(entries_table.c.id == entry_id))


def delete_all_entries() -> None:
    with get_conn() as conn:
        conn.execute(delete(entries_table))


def fetch_entries(
    start: Optional[date] = None,
    end: Optional[date] = None,
    categories: Optional[list[str]] = None,
) -> list[dict]:
    stmt = select(entries_table)
    if start:
        stmt = stmt.where(entries_table.c.entry_date >= start)
    if end:
        stmt = stmt.where(entries_table.c.entry_date <= end)
    if categories:
        stmt = stmt.where(entries_table.c.category.in_(categories))
    stmt = stmt.order_by(entries_table.c.entry_date.asc(), entries_table.c.id.asc())
    with get_conn() as conn:
        rows = conn.execute(stmt).mappings().all()
        return [dict(r) for r in rows]


def fetch_categories() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            select(entries_table.c.category).distinct().order_by(entries_table.c.category)
        ).all()
        return [r[0] for r in rows]


def add_goal(title: str, target: float, deadline: Optional[date]) -> int:
    if not title:
        raise ValueError("title is required")
    if target is None or float(target) <= 0:
        raise ValueError("target must be > 0")
    with get_conn() as conn:
        result = conn.execute(
            insert(goals_table).values(title=title, target=float(target), deadline=deadline)
        )
        return int(result.inserted_primary_key[0])


def fetch_goals() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            select(goals_table).order_by(goals_table.c.created_at.desc())
        ).mappings().all()
        return [dict(r) for r in rows]


def delete_goal(goal_id: int) -> None:
    with get_conn() as conn:
        conn.execute(delete(goals_table).where(goals_table.c.id == goal_id))


def health_check() -> bool:
    try:
        with get_conn() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def seed_demo_data() -> None:
    """Populate DB with realistic demo data if entries table is empty."""
    import random

    with get_conn() as conn:
        cnt = conn.execute(select(func.count()).select_from(entries_table)).scalar()
    if cnt and cnt > 0:
        return
    rng = random.Random(42)
    categories = [
        ("Зарплата", 80000, 15000, "Основная работа"),
        ("Фриланс", 25000, 12000, "Заказчик"),
        ("Инвестиции", 8000, 6000, "Дивиденды"),
        ("Подработка", 5000, 3000, "Разовая работа"),
        ("Кешбэк", 1500, 800, "Банк"),
    ]
    today = date.today()
    for days_ago in range(180, 0, -3):
        d = date.fromordinal(today.toordinal() - days_ago)
        for cat, base, var, source in categories:
            if rng.random() < 0.35:
                amount = max(0.01, round(base / 6 + rng.uniform(-var / 4, var / 4), 2))
                add_entry(amount, d, cat, source=source, note="")
