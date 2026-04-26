from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def to_dataframe(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "amount",
                "currency",
                "category",
                "source",
                "note",
                "entry_date",
                "created_at",
            ]
        )
    df = pd.DataFrame(rows)
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["amount"] = df["amount"].astype(float)
    return df


def daily_totals(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["entry_date", "amount"])
    out = (
        df.groupby(df["entry_date"].dt.date)["amount"]
        .sum()
        .reset_index()
        .rename(columns={"entry_date": "entry_date"})
    )
    out["entry_date"] = pd.to_datetime(out["entry_date"])
    return out


def monthly_totals(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", "amount"])
    g = df.copy()
    g["month"] = g["entry_date"].dt.to_period("M").dt.to_timestamp()
    out = g.groupby("month")["amount"].sum().reset_index()
    return out


def category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category", "amount", "share"])
    out = (
        df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
    )
    total = out["amount"].sum()
    out["share"] = (out["amount"] / total * 100) if total else 0
    return out


def cumulative(df: pd.DataFrame) -> pd.DataFrame:
    daily = daily_totals(df)
    if daily.empty:
        return daily
    daily = daily.sort_values("entry_date")
    daily["cumulative"] = daily["amount"].cumsum()
    return daily


def moving_average(df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    daily = daily_totals(df).sort_values("entry_date")
    if daily.empty:
        return daily
    full_idx = pd.date_range(daily["entry_date"].min(), daily["entry_date"].max(), freq="D")
    daily = daily.set_index("entry_date").reindex(full_idx, fill_value=0).rename_axis("entry_date").reset_index()
    daily[f"ma_{window}"] = daily["amount"].rolling(window=window, min_periods=1).mean()
    return daily


def kpi_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "total": 0.0,
            "avg_per_day": 0.0,
            "median_entry": 0.0,
            "max_entry": 0.0,
            "entries": 0,
            "active_days": 0,
            "best_day_amount": 0.0,
            "best_day_date": None,
            "top_category": None,
            "top_category_amount": 0.0,
        }
    total = float(df["amount"].sum())
    daily = daily_totals(df)
    days_span = max(1, (daily["entry_date"].max() - daily["entry_date"].min()).days + 1)
    avg_per_day = total / days_span
    best_idx = daily["amount"].idxmax()
    cat = category_breakdown(df).iloc[0]
    return {
        "total": total,
        "avg_per_day": avg_per_day,
        "median_entry": float(df["amount"].median()),
        "max_entry": float(df["amount"].max()),
        "entries": int(len(df)),
        "active_days": int(daily["entry_date"].nunique()),
        "best_day_amount": float(daily.loc[best_idx, "amount"]),
        "best_day_date": daily.loc[best_idx, "entry_date"].date(),
        "top_category": str(cat["category"]),
        "top_category_amount": float(cat["amount"]),
    }


def month_over_month(df: pd.DataFrame) -> dict:
    monthly = monthly_totals(df)
    if len(monthly) < 2:
        return {"prev": None, "curr": None, "delta": 0.0, "percent": 0.0}
    prev = float(monthly.iloc[-2]["amount"])
    curr = float(monthly.iloc[-1]["amount"])
    delta = curr - prev
    percent = (delta / prev * 100) if prev else 0.0
    return {"prev": prev, "curr": curr, "delta": delta, "percent": percent}


def forecast(df: pd.DataFrame, horizon_days: int = 30) -> pd.DataFrame:
    """Linear regression forecast on daily totals (filled), returning future days."""
    daily = moving_average(df, window=7)
    if len(daily) < 7:
        return pd.DataFrame(columns=["entry_date", "forecast"])
    daily = daily.copy()
    daily["t"] = np.arange(len(daily))
    X = daily[["t"]].values
    y = daily["amount"].values
    model = LinearRegression().fit(X, y)
    last_t = daily["t"].iloc[-1]
    future_t = np.arange(last_t + 1, last_t + 1 + horizon_days).reshape(-1, 1)
    preds = model.predict(future_t)
    preds = np.clip(preds, a_min=0, a_max=None)
    last_date = daily["entry_date"].iloc[-1]
    future_dates = [last_date + pd.Timedelta(days=i + 1) for i in range(horizon_days)]
    return pd.DataFrame({"entry_date": future_dates, "forecast": preds})


def streak(df: pd.DataFrame) -> dict:
    """Longest and current streak of days with any income."""
    if df.empty:
        return {"current": 0, "longest": 0}
    days = sorted(set(df["entry_date"].dt.date))
    longest = current = 1
    longest_run = 1
    for i in range(1, len(days)):
        if (days[i] - days[i - 1]).days == 1:
            current += 1
            longest_run = max(longest_run, current)
        else:
            current = 1
    today = date.today()
    cur = 0
    cursor = today
    s = set(days)
    while cursor in s:
        cur += 1
        cursor -= timedelta(days=1)
    return {"current": cur, "longest": longest_run}
