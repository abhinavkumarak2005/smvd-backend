"""009 create notices

Revision ID: 009
Revises: 008
Create Date: 2026-06-25
"""

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title        TEXT NOT NULL,
            title_tamil  TEXT,
            body         TEXT NOT NULL,
            body_tamil   TEXT,
            category     TEXT DEFAULT 'general'
                             CHECK (category IN (
                                 'general','booking','holiday','event','urgent'
                             )),
            priority     INTEGER DEFAULT 0,
            status       TEXT DEFAULT 'draft'
                             CHECK (status IN ('draft','scheduled','active','expired')),
            published_at TIMESTAMPTZ,
            expires_at   TIMESTAMPTZ,
            created_by   UUID REFERENCES users(id),
            created_at   TIMESTAMPTZ DEFAULT NOW(),
            updated_at   TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_notices_status ON notices (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notices_published_at ON notices (published_at);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notices CASCADE;")
