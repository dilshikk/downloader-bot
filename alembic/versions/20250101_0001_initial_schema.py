"""Initial schema — create all tables

Revision ID: 0001
Revises: 
Create Date: 2025-01-01 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id      BIGINT PRIMARY KEY NOT NULL,
            username   TEXT,
            status     TEXT NOT NULL,
            language   TEXT NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id       BIGINT PRIMARY KEY NOT NULL,
            channel_name     TEXT NOT NULL,
            channel_username TEXT,
            channel_status   TEXT NOT NULL,
            channel_url      TEXT,
            created_at       TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            bot_name     TEXT NOT NULL,
            bot_username TEXT NOT NULL,
            bot_status   TEXT NOT NULL,
            bot_url      TEXT NOT NULL,
            created_at   TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS referals (
            referal_id           TEXT PRIMARY KEY NOT NULL,
            referal_name         TEXT NOT NULL,
            referal_members_count INTEGER NOT NULL,
            created_at           TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id         SERIAL PRIMARY KEY,
            tg_id      BIGINT NOT NULL,
            file_id    TEXT NOT NULL,
            title      TEXT NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            UNIQUE(tg_id, file_id)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS favorites")
    op.execute("DROP TABLE IF EXISTS referals")
    op.execute("DROP TABLE IF EXISTS bots")
    op.execute("DROP TABLE IF EXISTS channels")
    op.execute("DROP TABLE IF EXISTS users")
