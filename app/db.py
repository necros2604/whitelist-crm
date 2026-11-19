import os

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://crm:crm@localhost:5432/crm")

# открываем при старте приложения
# check - проверять соединение перед выдачей, чтобы после рестарта БД не отдать мёртвое
pool = ConnectionPool(
    DATABASE_URL,
    open=False,
    timeout=5,
    check=ConnectionPool.check_connection,
    # timezone=UTC - чтобы время из БД всегда приходило в UTC, как требует задание
    kwargs={"row_factory": dict_row, "options": "-c timezone=UTC"},
)


def get_conn():
    # commit если всё ок, rollback если было исключение
    with pool.connection() as conn:
        yield conn


Conn = Connection[dict]
