import os
from pathlib import Path

import psycopg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://crm:crm@localhost:5432/crm")
MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


def migrate() -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        conn.commit()

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                continue
            # каждая миграция в своей транзакции: если упала - откатится целиком
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            print(f"applied {path.name}")


if __name__ == "__main__":
    migrate()
