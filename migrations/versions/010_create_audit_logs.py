"""010 create audit_logs

Revision ID: 010
Revises: 009
Create Date: 2026-06-25
"""

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            action       TEXT NOT NULL,
            entity_type  TEXT,
            entity_id    UUID,
            actor_id     UUID,
            actor_role   TEXT,
            before_state JSONB,
            after_state  JSONB,
            ip_address   TEXT,
            user_agent   TEXT,
            severity     TEXT DEFAULT 'info'
                             CHECK (severity IN ('info','warning','error','critical')),
            created_at   TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs (entity_type, entity_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs (actor_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs (action);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs (created_at DESC);")

    # CRITICAL: audit_logs is immutable — revoke UPDATE and DELETE from service_role
    # This ensures no one can alter or erase audit history
    op.execute("REVOKE UPDATE, DELETE ON audit_logs FROM service_role;")


def downgrade() -> None:
    # Restore permissions before dropping
    op.execute("GRANT UPDATE, DELETE ON audit_logs TO service_role;")
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE;")
