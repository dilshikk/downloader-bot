import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Load .env so POSTGRES_* variables are available
# ---------------------------------------------------------------------------
try:
    import environs
    _env = environs.Env()
    _env.read_env()
except Exception:
    pass

import os

# Build database URL from individual env vars (same as bot's config.py)
_DB_URL = (
    f"postgresql+asyncpg://"
    f"{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}"
    f"/{os.environ['POSTGRES_DB']}"
)

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config
config.set_main_option("sqlalchemy.url", _DB_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# We do NOT use SQLAlchemy ORM models — set target_metadata to None
# so Alembic operates in "plain SQL" mode (each migration writes raw SQL).
target_metadata = None


# ---------------------------------------------------------------------------
# Run migrations
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
            )
        )
        await connection.run_sync(lambda _: context.run_migrations())

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
