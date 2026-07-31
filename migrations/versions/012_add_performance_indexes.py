"""add performance indexes

Revision ID: 012
Revises: 011
Create Date: 2026-06-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Dashboard bookings today
    op.create_index('idx_bookings_created_at', 'bookings', ['created_at'])
    
    # 2. Monthly Revenue
    op.create_index('idx_payments_created_at', 'payments', ['created_at'])
    
    # 3. List Pending Certificates
    op.create_index('idx_e_undiyal_cert_status_created_at', 'e_undiyal_transactions', ['certificate_status', 'created_at'])
    
    # 4. Audit Logs filter
    op.create_index('idx_audit_logs_action_created_at', 'audit_logs', ['action', sa.text('created_at DESC')])

    # 5. Search Users (pg_trgm extension)
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        op.execute("CREATE INDEX IF NOT EXISTS idx_users_phone_trgm ON users USING gin (phone gin_trgm_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS idx_users_email_trgm ON users USING gin (email gin_trgm_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS idx_users_full_name_trgm ON users USING gin (full_name gin_trgm_ops);")
    except Exception as e:
        print("Could not create pg_trgm extension or indexes. Non-superuser or extension unavailable:", e)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_users_full_name_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_users_email_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_users_phone_trgm;")
    op.drop_index('idx_audit_logs_action_created_at', table_name='audit_logs')
    op.drop_index('idx_e_undiyal_cert_status_created_at', table_name='e_undiyal_transactions')
    op.drop_index('idx_payments_created_at', table_name='payments')
    op.drop_index('idx_bookings_created_at', table_name='bookings')
