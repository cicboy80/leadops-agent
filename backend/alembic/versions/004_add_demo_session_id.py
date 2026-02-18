"""Add demo_session_id to leads and notifications

Revision ID: 004
Revises: 003
Create Date: 2026-02-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('leads', sa.Column('demo_session_id', sa.String(length=36), nullable=True))
    op.create_index('ix_leads_demo_session_id', 'leads', ['demo_session_id'])

    op.add_column('notifications', sa.Column('demo_session_id', sa.String(length=36), nullable=True))


def downgrade() -> None:
    op.drop_column('notifications', 'demo_session_id')

    op.drop_index('ix_leads_demo_session_id', table_name='leads')
    op.drop_column('leads', 'demo_session_id')
