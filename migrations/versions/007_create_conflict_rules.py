"""007 create conflict_rules

Revision ID: 007
Revises: 006
Create Date: 2026-06-25
"""

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS conflict_rules (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            service_a_id   UUID NOT NULL REFERENCES services(id),
            service_b_id   UUID NOT NULL REFERENCES services(id),
            rule_type      TEXT NOT NULL
                               CHECK (rule_type IN (
                                   'mutual_exclusion','session_exclusive',
                                   'a_blocks_b','requires_approval'
                               )),
            direction      TEXT DEFAULT 'bidirectional'
                               CHECK (direction IN ('bidirectional','a_to_b')),
            notice_text    TEXT,
            is_active      BOOLEAN DEFAULT TRUE,
            created_at     TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_conflict_service_a ON conflict_rules (service_a_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_conflict_service_b ON conflict_rules (service_b_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS conflict_rules CASCADE;")
