import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Make sure app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import get_settings

# Alembic Config object
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load DATABASE_URL from .env and transform for SQLAlchemy asyncpg driver
settings = get_settings()
db_url = settings.DATABASE_URL

# Supabase URLs come as postgresql:// or postgres:// — SQLAlchemy needs postgresql+asyncpg://
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# NOTE: Alembic migrations must run against the DIRECT connection (port 5432),
# NOT PgBouncer (port 6543). Replace port if needed:
if ":6543/" in db_url:
    db_url = db_url.replace(":6543/", ":5432/")

config.set_main_option("sqlalchemy.url", db_url)

# We don't use SQLModel metadata here — migrations are raw SQL via op.execute()
target_metadata = None


# ── Offline mode (generates SQL script without DB connection) ─────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connects to DB and runs migrations) ──────────────────────────
def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
