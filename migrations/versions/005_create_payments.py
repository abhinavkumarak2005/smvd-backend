"""005 create payments

Revision ID: 005
Revises: 004
Create Date: 2026-06-25
"""

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            booking_id          UUID REFERENCES bookings(id),
            e_undiyal_id        UUID,
            gateway_order_id    TEXT UNIQUE NOT NULL,
            gateway_payment_id  TEXT,
            gateway_refund_id   TEXT,
            amount_paise        INTEGER NOT NULL,
            currency            TEXT DEFAULT 'INR',
            status              TEXT DEFAULT 'initiated'
                                    CHECK (status IN (
                                        'initiated','success','failed','refunded','expired'
                                    )),
            payment_method      TEXT,
            paid_at             TIMESTAMPTZ,
            refunded_at         TIMESTAMPTZ,
            created_at          TIMESTAMPTZ DEFAULT NOW(),
            updated_at          TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_gateway_order_id ON payments (gateway_order_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_booking_id ON payments (booking_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payments CASCADE;")
