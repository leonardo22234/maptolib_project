"""Юнит-тесты для слоя БД (db.py)."""

from datetime import date, timedelta

import pytest


def test_init_creates_tables(fresh_db):
    # health_check выполняет SELECT 1, плюс проверим, что таблицы пусты
    assert fresh_db.health_check() is True
    assert fresh_db.fetch_entries() == []
    assert fresh_db.fetch_goals() == []


def test_add_entry_and_fetch(fresh_db):
    new_id = fresh_db.add_entry(
        amount=1500.50,
        entry_date=date(2026, 1, 15),
        category="Зарплата",
        source="ООО Ромашка",
        note="январь",
        currency="RUB",
    )
    assert isinstance(new_id, int) and new_id > 0

    rows = fresh_db.fetch_entries()
    assert len(rows) == 1
    row = rows[0]
    assert row["amount"] == pytest.approx(1500.50)
    assert row["category"] == "Зарплата"
    assert row["source"] == "ООО Ромашка"
    assert row["currency"] == "RUB"


def test_add_entry_validates_amount(fresh_db):
    with pytest.raises(ValueError):
        fresh_db.add_entry(
            amount=0, entry_date=date.today(), category="Зарплата"
        )
    with pytest.raises(ValueError):
        fresh_db.add_entry(
            amount=-10, entry_date=date.today(), category="Зарплата"
        )


def test_add_entry_requires_category(fresh_db):
    with pytest.raises(ValueError):
        fresh_db.add_entry(amount=100, entry_date=date.today(), category="")


def test_update_entry(fresh_db):
    eid = fresh_db.add_entry(
        amount=100, entry_date=date(2026, 1, 1), category="Фриланс"
    )
    fresh_db.update_entry(
        eid,
        amount=200,
        entry_date=date(2026, 2, 1),
        category="Зарплата",
        source="X",
        note="upd",
        currency="USD",
    )
    row = fresh_db.fetch_entries()[0]
    assert row["amount"] == 200
    assert row["category"] == "Зарплата"
    assert row["currency"] == "USD"
    assert row["source"] == "X"
    assert row["entry_date"] == date(2026, 2, 1)


def test_delete_entry(fresh_db):
    a = fresh_db.add_entry(amount=10, entry_date=date.today(), category="A")
    b = fresh_db.add_entry(amount=20, entry_date=date.today(), category="B")
    fresh_db.delete_entry(a)
    rows = fresh_db.fetch_entries()
    assert {r["id"] for r in rows} == {b}


def test_filter_by_date_and_category(fresh_db):
    fresh_db.add_entry(100, date(2026, 1, 1), "Зарплата")
    fresh_db.add_entry(200, date(2026, 2, 1), "Фриланс")
    fresh_db.add_entry(300, date(2026, 3, 1), "Фриланс")

    rows = fresh_db.fetch_entries(start=date(2026, 2, 1))
    assert len(rows) == 2
    rows = fresh_db.fetch_entries(end=date(2026, 1, 31))
    assert len(rows) == 1
    rows = fresh_db.fetch_entries(categories=["Фриланс"])
    assert {r["category"] for r in rows} == {"Фриланс"}
    rows = fresh_db.fetch_entries(
        start=date(2026, 1, 1), end=date(2026, 2, 28), categories=["Фриланс"]
    )
    assert len(rows) == 1 and rows[0]["amount"] == 200


def test_fetch_categories_distinct_and_sorted(fresh_db):
    fresh_db.add_entry(10, date.today(), "B")
    fresh_db.add_entry(10, date.today(), "A")
    fresh_db.add_entry(10, date.today(), "B")
    assert fresh_db.fetch_categories() == ["A", "B"]


def test_goal_crud(fresh_db):
    gid = fresh_db.add_goal("Ноут", 150_000, date.today() + timedelta(days=120))
    goals = fresh_db.fetch_goals()
    assert len(goals) == 1 and goals[0]["title"] == "Ноут"
    fresh_db.delete_goal(gid)
    assert fresh_db.fetch_goals() == []


def test_goal_validation(fresh_db):
    with pytest.raises(ValueError):
        fresh_db.add_goal("", 100, None)
    with pytest.raises(ValueError):
        fresh_db.add_goal("X", 0, None)


def test_seed_demo_data_idempotent(fresh_db):
    fresh_db.seed_demo_data()
    n1 = len(fresh_db.fetch_entries())
    assert n1 > 0
    fresh_db.seed_demo_data()  # должна быть no-op, если уже есть данные
    n2 = len(fresh_db.fetch_entries())
    assert n1 == n2
