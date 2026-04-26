from __future__ import annotations

import io
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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
from db import (
    add_entry,
    add_goal,
    delete_all_entries,
    delete_entry,
    delete_goal,
    fetch_categories,
    fetch_entries,
    fetch_goals,
    init_db,
    seed_demo_data,
    update_entry,
)

st.set_page_config(
    page_title="Income Lab — Учёт доходов",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()


DEFAULT_CATEGORIES = [
    "Зарплата",
    "Фриланс",
    "Инвестиции",
    "Подработка",
    "Кешбэк",
    "Подарок",
    "Другое",
]


def _fmt(amount: float, currency: str = "RUB") -> str:
    sign = "₽" if currency == "RUB" else currency
    return f"{amount:,.2f} {sign}".replace(",", " ").replace(".", ",")


# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💸 Income Lab")
    st.caption("Серьёзный учёт доходов и аналитика")

    page = st.radio(
        "Раздел",
        ["📊 Дашборд", "➕ Записи", "🎯 Цели", "📥 Импорт / Экспорт", "⚙️ Настройки"],
        label_visibility="collapsed",
    )

    st.divider()
    all_cats = sorted(set(DEFAULT_CATEGORIES + fetch_categories()))
    today = date.today()
    default_start = today - timedelta(days=180)

    st.subheader("Фильтры")
    period = st.selectbox(
        "Период",
        ["Последние 30 дней", "Последние 90 дней", "Последние 180 дней", "Год", "Всё время", "Свой период"],
        index=2,
    )
    if period == "Последние 30 дней":
        start, end = today - timedelta(days=30), today
    elif period == "Последние 90 дней":
        start, end = today - timedelta(days=90), today
    elif period == "Последние 180 дней":
        start, end = today - timedelta(days=180), today
    elif period == "Год":
        start, end = today - timedelta(days=365), today
    elif period == "Всё время":
        start, end = None, None
    else:
        start = st.date_input("С", value=default_start)
        end = st.date_input("По", value=today)

    selected_cats = st.multiselect("Категории", all_cats, default=all_cats)

    st.divider()
    if st.button("✨ Заполнить демо-данными", use_container_width=True):
        seed_demo_data()
        st.success("Демо-данные добавлены")
        st.rerun()


rows = fetch_entries(start=start, end=end, categories=selected_cats or None)
df = to_dataframe(rows)


# ─── DASHBOARD ──────────────────────────────────────────────────────────────
def render_dashboard() -> None:
    st.title("📊 Дашборд")
    st.caption("Все цифры по выбранному периоду и категориям")

    if df.empty:
        st.info("Нет данных за выбранный период. Добавьте запись или загрузите демо-данные в боковой панели.")
        return

    kpi = kpi_summary(df)
    mom = month_over_month(df)
    s = streak(df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Всего", _fmt(kpi["total"]))
    c2.metric("В среднем за день", _fmt(kpi["avg_per_day"]))
    c3.metric(
        "За этот месяц",
        _fmt(mom["curr"]) if mom["curr"] is not None else "—",
        delta=f"{mom['percent']:+.1f}% к прошлому" if mom["curr"] is not None else None,
    )
    c4.metric("Записей", f"{kpi['entries']}", delta=f"{kpi['active_days']} активных дней")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Лучший день", _fmt(kpi["best_day_amount"]), delta=str(kpi["best_day_date"]))
    c6.metric("Топ-категория", kpi["top_category"], delta=_fmt(kpi["top_category_amount"]))
    c7.metric("Медиана записи", _fmt(kpi["median_entry"]))
    c8.metric(
        "Серия дней с доходом",
        f"🔥 {s['current']}",
        delta=f"рекорд: {s['longest']}",
    )

    st.divider()

    # Динамика + скользящее среднее
    daily = moving_average(df, window=7)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=daily["entry_date"],
            y=daily["amount"],
            name="Доход за день",
            marker_color="rgba(34,197,94,0.55)",
            hovertemplate="%{x|%d.%m.%Y}<br>%{y:,.0f} ₽<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["entry_date"],
            y=daily["ma_7"],
            mode="lines",
            name="MA-7",
            line=dict(color="#fbbf24", width=3),
            hovertemplate="%{x|%d.%m.%Y}<br>MA-7: %{y:,.0f} ₽<extra></extra>",
        )
    )
    fig.update_layout(
        title="Динамика доходов и сглаживание (7 дней)",
        height=420,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    )
    st.plotly_chart(fig, use_container_width=True)

    g1, g2 = st.columns([1, 1])
    with g1:
        cb = category_breakdown(df)
        pie = px.pie(
            cb,
            names="category",
            values="amount",
            hole=0.55,
            title="Структура доходов по категориям",
            color_discrete_sequence=px.colors.sequential.Emrld,
        )
        pie.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(pie, use_container_width=True)

    with g2:
        m = monthly_totals(df)
        bar = px.bar(
            m,
            x="month",
            y="amount",
            title="Доход по месяцам",
            color="amount",
            color_continuous_scale="Emrld",
        )
        bar.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=50, b=10),
            coloraxis_showscale=False,
            xaxis=dict(showgrid=False, title=None),
            yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title=None),
        )
        st.plotly_chart(bar, use_container_width=True)

    # Накопительный + прогноз
    cum = cumulative(df)
    fc = forecast(df, horizon_days=30)
    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=cum["entry_date"],
            y=cum["cumulative"],
            mode="lines",
            name="Накопительный доход",
            line=dict(color="#22c55e", width=3),
            fill="tozeroy",
            fillcolor="rgba(34,197,94,0.15)",
        )
    )
    if not fc.empty:
        last_cum = cum["cumulative"].iloc[-1] if not cum.empty else 0
        fc_cum = last_cum + fc["forecast"].cumsum()
        fig2.add_trace(
            go.Scatter(
                x=fc["entry_date"],
                y=fc_cum,
                mode="lines",
                name="Прогноз на 30 дней",
                line=dict(color="#fbbf24", width=2, dash="dash"),
            )
        )
    fig2.update_layout(
        title="Накопительный доход + прогноз",
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Таблица топ-источников
    st.subheader("Топ-источники")
    if "source" in df.columns:
        src = (
            df[df["source"].astype(str) != ""]
            .groupby("source")["amount"]
            .agg(["sum", "count", "mean"])
            .reset_index()
            .sort_values("sum", ascending=False)
            .head(10)
        )
        if not src.empty:
            src.columns = ["Источник", "Сумма", "Записей", "Средняя"]
            src["Сумма"] = src["Сумма"].map(lambda x: _fmt(x))
            src["Средняя"] = src["Средняя"].map(lambda x: _fmt(x))
            st.dataframe(src, use_container_width=True, hide_index=True)
        else:
            st.caption("У записей не указан источник.")


# ─── ENTRIES ────────────────────────────────────────────────────────────────
def render_entries() -> None:
    st.title("➕ Записи о доходах")

    with st.form("add_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 1, 1])
        amount = c1.number_input("Сумма", min_value=0.0, step=100.0, value=0.0, format="%.2f")
        cat = c2.selectbox("Категория", DEFAULT_CATEGORIES, index=0)
        currency = c3.selectbox("Валюта", ["RUB", "USD", "EUR", "KZT", "BYN", "UAH"], index=0)
        c4, c5 = st.columns([1, 2])
        d = c4.date_input("Дата", value=date.today())
        source = c5.text_input("Источник (например: ООО Ромашка)")
        note = st.text_area("Заметка", height=68, placeholder="Подробности, проект, клиент...")
        submitted = st.form_submit_button("Сохранить запись", use_container_width=True, type="primary")
        if submitted:
            if amount <= 0:
                st.error("Сумма должна быть больше нуля.")
            else:
                add_entry(amount, d, cat, source=source, note=note, currency=currency)
                st.success(f"Записал доход {_fmt(amount, currency)} ({cat})")
                st.rerun()

    st.divider()
    st.subheader("История")
    if df.empty:
        st.info("Записей ещё нет.")
        return

    view = df.sort_values(["entry_date", "id"], ascending=False).copy()
    view["entry_date"] = view["entry_date"].dt.date

    edited = st.data_editor(
        view[["id", "entry_date", "amount", "currency", "category", "source", "note"]],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=["id"],
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "entry_date": st.column_config.DateColumn("Дата"),
            "amount": st.column_config.NumberColumn("Сумма", format="%.2f"),
            "currency": st.column_config.SelectboxColumn("Валюта", options=["RUB", "USD", "EUR", "KZT", "BYN", "UAH"]),
            "category": st.column_config.SelectboxColumn("Категория", options=sorted(set(DEFAULT_CATEGORIES + all_cats))),
            "source": st.column_config.TextColumn("Источник"),
            "note": st.column_config.TextColumn("Заметка"),
        },
        key="entries_editor",
    )

    cols = st.columns([1, 1, 4])
    if cols[0].button("💾 Сохранить изменения", use_container_width=True):
        original_by_id = {int(r["id"]): r for _, r in view.iterrows()}
        changes = 0
        for _, r in edited.iterrows():
            orig = original_by_id.get(int(r["id"]))
            if orig is None:
                continue
            if (
                float(r["amount"]) != float(orig["amount"])
                or r["entry_date"] != orig["entry_date"]
                or r["category"] != orig["category"]
                or (r["source"] or "") != (orig["source"] or "")
                or (r["note"] or "") != (orig["note"] or "")
                or r["currency"] != orig["currency"]
            ):
                update_entry(
                    int(r["id"]),
                    float(r["amount"]),
                    r["entry_date"],
                    str(r["category"]),
                    str(r["source"] or ""),
                    str(r["note"] or ""),
                    str(r["currency"]),
                )
                changes += 1
        st.success(f"Обновлено записей: {changes}")
        st.rerun()

    st.divider()
    with st.expander("🗑 Удалить запись"):
        ids = view["id"].tolist()
        if ids:
            sel = st.selectbox(
                "Выберите запись",
                ids,
                format_func=lambda i: (
                    f"#{i} — {view[view['id']==i].iloc[0]['entry_date']} • "
                    f"{_fmt(float(view[view['id']==i].iloc[0]['amount']), view[view['id']==i].iloc[0]['currency'])} • "
                    f"{view[view['id']==i].iloc[0]['category']}"
                ),
            )
            if st.button("Удалить", type="secondary"):
                delete_entry(int(sel))
                st.success("Удалено.")
                st.rerun()


# ─── GOALS ──────────────────────────────────────────────────────────────────
def render_goals() -> None:
    st.title("🎯 Финансовые цели")
    st.caption("Накопить на ноут, отпуск или подушку безопасности")

    with st.form("goal_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        title = c1.text_input("Название цели", placeholder="Например: новый ноутбук")
        target = c2.number_input("Целевая сумма", min_value=0.0, step=1000.0, value=0.0)
        deadline = c3.date_input("Дедлайн (необязательно)", value=date.today() + timedelta(days=180))
        if st.form_submit_button("Добавить цель", use_container_width=True, type="primary"):
            if title and target > 0:
                add_goal(title, target, deadline)
                st.success("Цель добавлена.")
                st.rerun()
            else:
                st.error("Заполните название и сумму.")

    st.divider()
    goals = fetch_goals()
    if not goals:
        st.info("Пока нет целей. Добавьте первую выше.")
        return

    total_income = float(df["amount"].sum()) if not df.empty else 0.0
    for g in goals:
        progress = min(1.0, total_income / g["target"]) if g["target"] else 0
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"### {g['title']}")
            c1.caption(
                f"Цель: **{_fmt(g['target'])}**"
                + (f" • Дедлайн: **{g['deadline']}**" if g.get("deadline") else "")
            )
            c1.progress(progress, text=f"{progress*100:.1f}% ({_fmt(total_income)} из {_fmt(g['target'])})")
            if c2.button("Удалить", key=f"del_goal_{g['id']}"):
                delete_goal(int(g["id"]))
                st.rerun()


# ─── IMPORT / EXPORT ────────────────────────────────────────────────────────
def render_io() -> None:
    st.title("📥 Импорт и экспорт")

    st.subheader("Экспорт")
    if df.empty:
        st.info("Нет данных для экспорта.")
    else:
        export_df = df.copy()
        export_df["entry_date"] = export_df["entry_date"].dt.strftime("%Y-%m-%d")
        csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Скачать CSV",
            data=csv,
            file_name=f"income_{date.today().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="entries")
        st.download_button(
            "Скачать Excel",
            data=buf.getvalue(),
            file_name=f"income_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            disabled=True,
            help="Установите openpyxl для экспорта в Excel",
        )

    st.divider()
    st.subheader("Импорт CSV")
    st.caption(
        "Нужны колонки: amount, entry_date (YYYY-MM-DD), category. Опционально: source, note, currency."
    )
    uploaded = st.file_uploader("CSV-файл", type=["csv"])
    if uploaded is not None:
        try:
            up_df = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Не удалось прочитать файл: {e}")
            return
        st.dataframe(up_df.head(20), use_container_width=True)
        if st.button("Импортировать", type="primary"):
            ok, fail = 0, 0
            for _, r in up_df.iterrows():
                try:
                    add_entry(
                        amount=float(r["amount"]),
                        entry_date=pd.to_datetime(r["entry_date"]).date(),
                        category=str(r.get("category", "Другое")),
                        source=str(r.get("source", "") or ""),
                        note=str(r.get("note", "") or ""),
                        currency=str(r.get("currency", "RUB") or "RUB"),
                    )
                    ok += 1
                except Exception:
                    fail += 1
            st.success(f"Импортировано: {ok}. Пропущено: {fail}")
            st.rerun()


# ─── SETTINGS ───────────────────────────────────────────────────────────────
def render_settings() -> None:
    st.title("⚙️ Настройки")

    st.subheader("Опасная зона")
    st.warning("Удаление данных необратимо.")
    confirm = st.text_input('Введите слово "УДАЛИТЬ" для подтверждения', value="")
    if st.button("Удалить ВСЕ записи", type="secondary"):
        if confirm == "УДАЛИТЬ":
            delete_all_entries()
            st.success("База очищена.")
            st.rerun()
        else:
            st.error("Подтверждение не совпало.")

    st.divider()
    st.subheader("О проекте")
    st.markdown(
        """
        **Income Lab** — серьёзная версия трекера доходов:
        - SQLite-база, фильтры по категориям и периоду
        - KPI: средний доход, медиана, MoM, серии активности
        - Графики: динамика, MA-7, по категориям, по месяцам, накопительный
        - Прогноз на 30 дней (линейная регрессия)
        - Цели накоплений с прогрессом
        - Импорт / экспорт CSV
        """
    )


PAGES = {
    "📊 Дашборд": render_dashboard,
    "➕ Записи": render_entries,
    "🎯 Цели": render_goals,
    "📥 Импорт / Экспорт": render_io,
    "⚙️ Настройки": render_settings,
}
PAGES[page]()
