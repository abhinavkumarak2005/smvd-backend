"""003 create slot_inventory

Revision ID: 003
Revises: 002
Create Date: 2026-06-25
"""

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS slot_inventory (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            service_id      UUID NOT NULL REFERENCES services(id),
            date            DATE NOT NULL,
            session         TEXT DEFAULT 'na',
            total_capacity  INTEGER NOT NULL,
            confirmed_count INTEGER DEFAULT 0 CHECK (confirmed_count >= 0),
            pending_count   INTEGER DEFAULT 0 CHECK (pending_count >= 0),
            is_blocked      BOOLEAN DEFAULT FALSE,
            block_reason    TEXT,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW(),

            CONSTRAINT uq_slot_service_date_session
                UNIQUE (service_id, date, session)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_slot_service_date ON slot_inventory (service_id, date);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_slot_date ON slot_inventory (date);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS slot_inventory CASCADE;")
