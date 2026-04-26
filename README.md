# 💸 Income Lab

Серьёзный учёт доходов на **Streamlit + PostgreSQL** с дашбордом, аналитикой,
прогнозом на 30 дней и целями накоплений. Под капотом — SQLAlchemy 2.0,
поэтому одно и то же приложение работает и поверх PostgreSQL (прод, через
docker-compose), и поверх SQLite (локально / тесты).

---

## ✨ Возможности

- **Дашборд:** 8 KPI (всего, среднее за день, MoM, серия активных дней,
  топ-категория, медиана и пр.), графики динамики с MA-7, пирог по
  категориям, месячные столбцы, накопительный доход.
- **Прогноз** на 30 дней по линейной регрессии (`scikit-learn`).
- **Записи:** редактируемая таблица, добавление, удаление, мульти-валюты.
- **Цели накоплений** с прогресс-баром и дедлайном.
- **Импорт/экспорт CSV.**
- **PostgreSQL в проде** (Docker), SQLite — для дев и тестов.
- **Тесты:** 22+ юнит-теста и интеграционный сквозной пайплайн.

---

## 🚀 Быстрый старт

### Вариант A — продовый стек (PostgreSQL в Docker)

```bash
cp .env.example .env
docker compose up -d postgres        # поднимаем БД
pip install -r requirements.txt
streamlit run app.py --server.port 5000
```

Adminer (веб-клиент к Postgres) будет доступен на `http://localhost:8088`
(сервер `postgres`, юзер/пароль/БД — из `.env`).

### Вариант B — локально на SQLite

```bash
cp .env.example .env
# в .env закомментируй PostgreSQL и раскомментируй SQLite-строку
pip install -r requirements.txt
streamlit run app.py --server.port 5000
```

---

## ⚙️ Переменные окружения

Полный пример — в [`.env.example`](./.env.example).

| Переменная | Назначение | Пример |
| --- | --- | --- |
| `DATABASE_URL` | URL подключения SQLAlchemy. Поддерживается PostgreSQL и SQLite. | `postgresql+psycopg2://incomelab:incomelab@localhost:5432/incomelab` |
| `APP_PORT` | Порт Streamlit-сервера. | `5000` |
| `APP_ENV` | Метка окружения. | `development` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` / `POSTGRES_PORT` | Используются `docker-compose.yml` для инициализации Postgres. | `incomelab` |

`DATABASE_URL` читается через `python-dotenv` при старте приложения.

---

## 🐳 Docker / Postgres

`docker-compose.yml` поднимает два сервиса:

- **postgres** (`postgres:16-alpine`) с healthcheck и постоянным томом
  `incomelab_pgdata`.
- **adminer** — веб-интерфейс к БД на `http://localhost:8088`.

Полезные команды:

```bash
docker compose up -d           # запустить
docker compose ps              # статус
docker compose logs -f postgres
docker compose down            # остановить (данные сохранятся)
docker compose down -v         # остановить и удалить том
```

---

## 🧪 Тесты

```bash
pip install -r requirements.txt
pytest
```

- Все юнит-тесты прогоняются на SQLite-в-памяти, не требуют внешних
  зависимостей и запускаются за секунды.
- Интеграционный тест `test_postgres_roundtrip` автоматически
  **skip-ается**, если Postgres не запущен. Чтобы прогнать его против
  docker-compose:

  ```bash
  docker compose up -d postgres
  TEST_DATABASE_URL="postgresql+psycopg2://incomelab:incomelab@localhost:5432/incomelab" pytest
  ```

---

## 🗂 Структура

```
python-app/
├── app.py                # Streamlit UI
├── analytics.py          # KPI, агрегации, прогноз
├── db.py                 # SQLAlchemy слой (Postgres/SQLite)
├── requirements.txt
├── pyproject.toml
├── .env.example
├── docker-compose.yml
├── .streamlit/config.toml
├── data/                 # SQLite-файл (только локально)
└── tests/
    ├── conftest.py       # фикстуры fresh_db / pg_db
    ├── test_db.py        # юниты: CRUD, валидация, фильтры
    ├── test_analytics.py # юниты: KPI / прогноз / streak
    └── test_integration.py
```

---

## 🛠 Стек

Python 3.11 · Streamlit · SQLAlchemy 2 · PostgreSQL 16 · Plotly ·
pandas · scikit-learn · pytest · Docker Compose.
