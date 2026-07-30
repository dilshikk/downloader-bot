"""Fix favorites table — ensure tg_id column exists

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-02 00:00:00

On servers where the favorites table was created without the tg_id column
(old schema), this migration recreates the table with the correct schema.
Existing rows are lost, but the table was broken anyway.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if tg_id is missing; if so, drop and recreate the table.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'favorites' AND column_name = 'tg_id'
            ) THEN
                DROP TABLE IF EXISTS favorites;
                CREATE TABLE favorites (
                    id         SERIAL PRIMARY KEY,
                    tg_id      BIGINT NOT NULL,
                    file_id    TEXT NOT NULL,
                    title      TEXT NOT NULL,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    UNIQUE(tg_id, file_id)
                );
                RAISE NOTICE 'favorites recreated with correct schema';
            ELSE
                RAISE NOTICE 'favorites already has tg_id, skipping';
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    # Cannot safely reverse — would need to know original schema.
    pass
