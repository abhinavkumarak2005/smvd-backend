"""002 create services

Revision ID: 002
Revises: 001
Create Date: 2026-06-25
"""

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name                 TEXT NOT NULL,
            name_tamil           TEXT,
            category             TEXT CHECK (category IN (
                                     'archanai','homam','seva',
                                     'chariot','annadhanam','special'
                                 )),
            description          TEXT,
            description_tamil    TEXT,
            price_paise          INTEGER NOT NULL,
            max_persons          INTEGER DEFAULT 5,
            advance_booking_days INTEGER DEFAULT 1,
            session              TEXT CHECK (session IN ('morning','evening','both','na'))
                                     DEFAULT 'na',
            is_active            BOOLEAN DEFAULT TRUE,
            image_url            TEXT,
            sort_order           INTEGER DEFAULT 0,
            created_at           TIMESTAMPTZ DEFAULT NOW(),
            updated_at           TIMESTAMPTZ DEFAULT NOW()
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS services CASCADE;")
