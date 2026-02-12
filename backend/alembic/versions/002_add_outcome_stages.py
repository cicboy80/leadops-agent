"""Add outcome stages

Revision ID: 002
Revises: 001
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add outcome stage columns to leads table
    op.add_column('leads', sa.Column('current_outcome_stage', sa.String(length=30), nullable=True))
    op.add_column('leads', sa.Column('outcome_stage_entered_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_leads_current_outcome_stage', 'leads', ['current_outcome_stage'])

    # Create lead_outcome_stages table
    op.create_table(
        'lead_outcome_stages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage', sa.String(length=30), nullable=False),
        sa.Column('previous_stage', sa.String(length=30), nullable=True),
        sa.Column('reason', sa.String(length=30), nullable=False),
        sa.Column('triggered_by', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('entered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('exited_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lead_outcome_stages_lead_id', 'lead_outcome_stages', ['lead_id'])
    op.create_index('ix_lead_outcome_stages_stage', 'lead_outcome_stages', ['stage'])
    op.create_index('ix_lead_outcome_stages_entered_at', 'lead_outcome_stages', ['entered_at'])
    op.create_index('ix_lead_outcome_stages_lead_id_stage', 'lead_outcome_stages', ['lead_id', 'stage'])


def downgrade() -> None:
    op.drop_index('ix_lead_outcome_stages_lead_id_stage', table_name='lead_outcome_stages')
    op.drop_index('ix_lead_outcome_stages_entered_at', table_name='lead_outcome_stages')
    op.drop_index('ix_lead_outcome_stages_stage', table_name='lead_outcome_stages')
    op.drop_index('ix_lead_outcome_stages_lead_id', table_name='lead_outcome_stages')
    op.drop_table('lead_outcome_stages')
    op.drop_index('ix_leads_current_outcome_stage', table_name='leads')
    op.drop_column('leads', 'outcome_stage_entered_at')
    op.drop_column('leads', 'current_outcome_stage')
