from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def apply_schema(engine: Engine) -> None:
    """Apply the PostgreSQL schema (pgvector extension, tables, forced row-level security).

    Every statement is idempotent. Non-PostgreSQL engines (local SQLite tests) are skipped.
    """
    if engine.dialect.name != "postgresql":
        return
    statements = [part.strip() for part in SCHEMA_PATH.read_text().split(";\n") if part.strip()]
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement.rstrip(";").replace("%", "%%"))
