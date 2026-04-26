"""Юнит-тесты для аналитики (analytics.py) — без БД."""

from datetime import date, timedelta

import pandas as pd
import pytest

from analytics import (
    category_breakdown,
    cumulative,
    daily_totals,
    forecast,
    kpi_summary,
    monthly_totals,
    month_over_month,
    moving_average,
    streak,
    to_dataframe,
)


def make_rows(items):
    """items = [(amount, date, category, source?)]"""
    rows = []
    for i, item in enumerate(items, start=1):
        amount, d, cat = item[0], item[1], item[2]
        source = item[3] if len(item) > 3 else ""
        rows.append(
            {
                "id": i,
                "amount": float(amount),
                "currency": "RUB",
                "category": cat,
                "source": source,
                "note": "",
                "entry_date": d.isoformat(),
                "created_at": "2026-01-01T00:00:00",
            }
        )
    return rows


def test_to_dataframe_empty():
    df = to_dataframe([])
    assert df.empty
    assert "amount" in df.columns


def test_daily_totals_aggregation():
    rows = make_rows(
        [
            (100, date(2026, 1, 1), "A"),
            (50, date(2026, 1, 1), "B"),
            (200, date(2026, 1, 2), "A"),
        ]
    )
    df = to_dataframe(rows)
    daily = daily_totals(df)
    assert len(daily) == 2
    assert float(daily.iloc[0]["amount"]) == 150
    assert float(daily.iloc[1]["amount"]) == 200


def test_monthly_totals():
    rows = make_rows(
        [
            (100, date(2026, 1, 5), "A"),
            (200, date(2026, 1, 25), "A"),
            (50, date(2026, 2, 1), "A"),
        ]
    )
    monthly = monthly_totals(to_dataframe(rows))
    assert len(monthly) == 2
    assert float(monthly.iloc[0]["amount"]) == 300
    assert float(monthly.iloc[1]["amount"]) == 50


def test_category_breakdown_shares_sum_to_100():
    rows = make_rows(
        [
            (300, date(2026, 1, 1), "A"),
            (100, date(2026, 1, 2), "B"),
            (100, date(2026, 1, 3), "C"),
        ]
    )
    cb = category_breakdown(to_dataframe(rows))
    assert list(cb["category"]) == ["A", "B", "C"]
    assert cb["share"].sum() == pytest.approx(100.0)
    assert cb.iloc[0]["share"] == pytest.approx(60.0)


def test_cumulative_is_monotonic():
    rows = make_rows(
        [(i * 10, date(2026, 1, i), "A") for i in range(1, 6)]
    )
    cum = cumulative(to_dataframe(rows))
    values = list(cum["cumulative"])
    assert values == sorted(values)
    assert values[-1] == pytest.approx(150)


def test_moving_average_fills_missing_days():
    rows = make_rows(
        [
            (100, date(2026, 1, 1), "A"),
            (100, date(2026, 1, 5), "A"),  # 4-дневный пропуск
        ]
    )
    ma = moving_average(to_dataframe(rows), window=3)
    # должны быть 5 строк (1..5 января), и MA-3 присутствует везде
    assert len(ma) == 5
    assert "ma_3" in ma.columns
    assert ma["ma_3"].isna().sum() == 0


def test_kpi_summary_counts_and_top_category():
    rows = make_rows(
        [
            (100, date(2026, 1, 1), "Зарплата"),
            (300, date(2026, 1, 2), "Зарплата"),
            (50, date(2026, 1, 3), "Фриланс"),
        ]
    )
    kpi = kpi_summary(to_dataframe(rows))
    assert kpi["entries"] == 3
    assert kpi["total"] == pytest.approx(450)
    assert kpi["top_category"] == "Зарплата"
    assert kpi["best_day_amount"] == pytest.approx(300)
    assert kpi["best_day_date"] == date(2026, 1, 2)


def test_month_over_month_delta_and_percent():
    rows = make_rows(
        [
            (100, date(2026, 1, 5), "A"),
            (200, date(2026, 2, 5), "A"),
        ]
    )
    mom = month_over_month(to_dataframe(rows))
    assert mom["prev"] == 100
    assert mom["curr"] == 200
    assert mom["delta"] == 100
    assert mom["percent"] == pytest.approx(100.0)


def test_month_over_month_handles_single_month():
    rows = make_rows([(100, date(2026, 1, 5), "A")])
    mom = month_over_month(to_dataframe(rows))
    assert mom["prev"] is None and mom["curr"] is None


def test_forecast_returns_horizon_and_non_negative():
    rows = make_rows(
        [(100 + i, date(2026, 1, 1) + timedelta(days=i), "A") for i in range(20)]
    )
    fc = forecast(to_dataframe(rows), horizon_days=10)
    assert len(fc) == 10
    assert (fc["forecast"] >= 0).all()


def test_forecast_too_few_points_returns_empty():
    rows = make_rows([(100, date(2026, 1, 1), "A")])
    fc = forecast(to_dataframe(rows), horizon_days=10)
    assert fc.empty


def test_streak_computes_longest_run():
    rows = make_rows(
        [
            (10, date(2026, 1, 1), "A"),
            (10, date(2026, 1, 2), "A"),
            (10, date(2026, 1, 3), "A"),
            (10, date(2026, 1, 10), "A"),
        ]
    )
    s = streak(to_dataframe(rows))
    assert s["longest"] == 3
