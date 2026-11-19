import os

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

# тесты идут в отдельную базу crm_test на том же сервере, чтобы не трогать рабочую
BASE_URL = os.getenv("DATABASE_URL", "postgresql://crm:crm@localhost:5432/crm")
TEST_DB = "crm_test"
TEST_URL = BASE_URL.rsplit("/", 1)[0] + "/" + TEST_DB

# подменяем до импорта app, потому что app.db читает DATABASE_URL при импорте
os.environ["DATABASE_URL"] = TEST_URL

from app.main import app  # noqa: E402
from app.migrate import migrate  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def test_db():
    # каждый запуск с чистой базы, чтобы схема всегда была как в миграциях
    with psycopg.connect(BASE_URL, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {TEST_DB}")
    migrate()


@pytest.fixture(autouse=True)
def clean_tables(test_db):
    # менеджеров не трогаем - они из миграции
    with psycopg.connect(TEST_URL) as conn:
        conn.execute("TRUNCATE calls, meeting_events, meetings, companies RESTART IDENTITY CASCADE")


# прямое соединение с тестовой базой - проверить, что реально записалось
@pytest.fixture
def db():
    with psycopg.connect(TEST_URL, row_factory=dict_row, autocommit=True) as conn:
        yield conn


# один клиент на все тесты: пул из app.db после close() заново не открывается
@pytest.fixture(scope="session")
def client(test_db):
    with TestClient(app) as c:
        yield c
