"""004 create bookings

Revision ID: 004
Revises: 003
Create Date: 2026-06-25
"""

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            booking_reference  TEXT UNIQUE NOT NULL,
            user_id            UUID NOT NULL REFERENCES users(id),
            service_id         UUID NOT NULL REFERENCES services(id),
            slot_id            UUID REFERENCES slot_inventory(id),
            booking_date       DATE NOT NULL,
            session            TEXT DEFAULT 'na',
            num_persons        INTEGER DEFAULT 1,
            amount_paise       INTEGER NOT NULL,
            status             TEXT DEFAULT 'pending_payment'
                                   CHECK (status IN (
                                       'pending_payment','confirmed','pending_approval',
                                       'approved','rejected','cancelled','expired','payment_failed'
                                   )),
            requires_approval  BOOLEAN DEFAULT FALSE,
            approval_note      TEXT,
            approved_by        UUID REFERENCES users(id),
            approved_at        TIMESTAMPTZ,
            cancelled_at       TIMESTAMPTZ,
            cancellation_note  TEXT,
            special_note       TEXT,
            created_at         TIMESTAMPTZ DEFAULT NOW(),
            updated_at         TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS booking_persons (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            booking_id  UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
            full_name   TEXT NOT NULL,
            star        TEXT NOT NULL,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bookings_service_date ON bookings (service_id, booking_date);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bookings_reference ON bookings (booking_reference);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_booking_persons_booking ON booking_persons (booking_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS booking_persons CASCADE;")
    op.execute("DROP TABLE IF EXISTS bookings CASCADE;")
