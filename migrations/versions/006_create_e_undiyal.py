"""006 create e_undiyal_transactions

Revision ID: 006
Revises: 005
Create Date: 2026-06-25
"""

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS e_undiyal_transactions (
            id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            transaction_reference      TEXT UNIQUE NOT NULL,
            user_id                    UUID REFERENCES users(id),
            donor_name                 TEXT NOT NULL,
            donor_phone                TEXT,
            donor_email                TEXT,
            amount_paise               INTEGER NOT NULL,
            donation_category          TEXT,
            status                     TEXT DEFAULT 'initiated'
                                           CHECK (status IN (
                                               'initiated','success','failed','refunded'
                                           )),
            tax_certificate_eligible   BOOLEAN DEFAULT TRUE,
            certificate_status         TEXT DEFAULT 'pending_details'
                                           CHECK (certificate_status IN (
                                               'pending_details','processing',
                                               'ready','dispatched','delivered'
                                           )),
            delivery_mode              TEXT CHECK (delivery_mode IN ('in_person','courier')),
            donor_location_type        TEXT CHECK (donor_location_type IN (
                                           'local','domestic','international'
                                       )),
            donor_address              JSONB,
            certificate_number         TEXT UNIQUE,
            certificate_url            TEXT,
            courier_tracking_id        TEXT,
            courier_partner            TEXT,
            dispatched_at              TIMESTAMPTZ,
            details_submitted_at       TIMESTAMPTZ,
            certificate_issued_by      UUID REFERENCES users(id),
            certificate_issued_at      TIMESTAMPTZ,
            created_at                 TIMESTAMPTZ DEFAULT NOW(),
            updated_at                 TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_e_undiyal_user_id ON e_undiyal_transactions (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_e_undiyal_status ON e_undiyal_transactions (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_e_undiyal_cert_status ON e_undiyal_transactions (certificate_status);")

    # Add FK from payments to e_undiyal_transactions now that both tables exist
    op.execute("""
        ALTER TABLE payments
            ADD CONSTRAINT fk_payments_e_undiyal
            FOREIGN KEY (e_undiyal_id)
            REFERENCES e_undiyal_transactions(id);
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE payments DROP CONSTRAINT IF EXISTS fk_payments_e_undiyal;")
    op.execute("DROP TABLE IF EXISTS e_undiyal_transactions CASCADE;")
