"""Add reply classifications and notifications

Revision ID: 003
Revises: 002
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create reply_classifications table
    op.create_table(
        'reply_classifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reply_body', sa.Text(), nullable=False),
        sa.Column('classification', sa.String(length=30), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=False),
        sa.Column('extracted_dates', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_auto_reply', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('overridden_by', sa.String(length=255), nullable=True),
        sa.Column('overridden_classification', sa.String(length=30), nullable=True),
        sa.Column('overridden_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reply_classifications_lead_id', 'reply_classifications', ['lead_id'])

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_lead_id', 'notifications', ['lead_id'])
    op.create_index('ix_notifications_read_at', 'notifications', ['read_at'])


def downgrade() -> None:
    op.drop_index('ix_notifications_read_at', table_name='notifications')
    op.drop_index('ix_notifications_lead_id', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('ix_reply_classifications_lead_id', table_name='reply_classifications')
    op.drop_table('reply_classifications')
