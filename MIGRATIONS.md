# Migrations (Alembic)

The project uses **Alembic** for database schema migrations with an async PostgreSQL connection.

## Setup (first time)

```bash
pip install alembic "sqlalchemy[asyncio]"
```

Make sure your `.env` file contains the database variables:
```
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_HOST=...
POSTGRES_PORT=5432
POSTGRES_DB=...
```

## Run all pending migrations

```bash
alembic upgrade head
```

## Check current revision

```bash
alembic current
```

## Migration history

```bash
alembic history
```

## Create a new migration

```bash
alembic revision -m "describe your change"
```

Then edit the generated file in `alembic/versions/` and write raw SQL inside `upgrade()` and `downgrade()` using `op.execute()`.

## Rollback one step

```bash
alembic downgrade -1
```

## Migrations list

| Rev  | Description |
|------|-------------|
| 0001 | Initial schema (users, channels, bots, referals, favorites) |
| 0002 | Fix favorites table — ensure `tg_id` column exists |
