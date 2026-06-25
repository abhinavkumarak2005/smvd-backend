"""008 create calendar_dates

Revision ID: 008
Revises: 007
Create Date: 2026-06-25
"""

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS calendar_dates (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            date                DATE UNIQUE NOT NULL,
            status              TEXT DEFAULT 'open'
                                    CHECK (status IN ('open','blocked','partial')),
            notes               TEXT,
            notes_tamil         TEXT,
            allowed_service_ids JSONB DEFAULT '[]',
            created_by          UUID REFERENCES users(id),
            created_at          TIMESTAMPTZ DEFAULT NOW(),
            updated_at          TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_dates (date);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS calendar_dates CASCADE;")
