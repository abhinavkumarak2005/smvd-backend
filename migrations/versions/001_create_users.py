"""001 create users

Revision ID: 001
Revises:
Create Date: 2026-06-25
"""

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            phone           TEXT UNIQUE,
            email           TEXT UNIQUE,
            full_name       TEXT,
            role            TEXT DEFAULT 'devotee'
                                CHECK (role IN ('devotee','staff','admin','super_admin')),
            is_active       BOOLEAN DEFAULT TRUE,
            totp_secret     TEXT,
            totp_enabled    BOOLEAN DEFAULT FALSE,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users (phone);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
