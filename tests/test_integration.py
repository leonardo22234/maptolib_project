"""Интеграционные тесты: связка БД + аналитика, плюс опциональный PostgreSQL."""

from datetime import date, timedelta


def test_end_to_end_pipeline(fresh_db):
    """Пишем в БД и считаем аналитику поверх — проверяем сквозной пайплайн."""
    from analytics import kpi_summary, monthly_totals, to_dataframe

    base = date(2026, 1, 1)
    for i in range(0, 60):
        fresh_db.add_entry(
            amount=100 + i,
            entry_date=base + timedelta(days=i),
            category="Зарплата" if i % 2 == 0 else "Фриланс",
            source="src",
            note="",
        )

    rows = fresh_db.fetch_entries()
    df = to_dataframe(rows)
    kpi = kpi_summary(df)

    assert kpi["entries"] == 60
    assert kpi["total"] > 0
    assert kpi["top_category"] in {"Зарплата", "Фриланс"}

    monthly = monthly_totals(df)
    # январь + февраль + начало марта
    assert len(monthly) >= 2


def test_filter_then_aggregate(fresh_db):
    from analytics import kpi_summary, to_dataframe

    fresh_db.add_entry(100, date(2026, 1, 1), "A")
    fresh_db.add_entry(200, date(2026, 2, 1), "B")
    fresh_db.add_entry(300, date(2026, 3, 1), "A")

    rows = fresh_db.fetch_entries(categories=["A"])
    kpi = kpi_summary(to_dataframe(rows))
    assert kpi["entries"] == 2
    assert kpi["total"] == 400


def test_postgres_roundtrip(pg_db):
    """Проверяем, что весь CRUD честно работает на PostgreSQL.

    Тест автоматически skip-ается, если Postgres не запущен (см. conftest)."""
    eid = pg_db.add_entry(
        amount=1234.56,
        entry_date=date(2026, 4, 1),
        category="Зарплата",
        source="ООО Ромашка",
        note="апрель",
        currency="RUB",
    )
    rows = pg_db.fetch_entries()
    assert len(rows) == 1
    assert rows[0]["id"] == eid
    assert rows[0]["amount"] == 1234.56
    assert rows[0]["category"] == "Зарплата"

    pg_db.update_entry(
        eid,
        amount=9999,
        entry_date=date(2026, 4, 2),
        category="Фриланс",
        source="X",
        note="y",
        currency="USD",
    )
    row = pg_db.fetch_entries()[0]
    assert row["amount"] == 9999 and row["currency"] == "USD"

    pg_db.delete_entry(eid)
    assert pg_db.fetch_entries() == []
