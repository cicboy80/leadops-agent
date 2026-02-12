"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('api_key_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('first_name', sa.String(length=255), nullable=False),
        sa.Column('last_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('industry', sa.String(length=255), nullable=True),
        sa.Column('company_size', sa.String(length=50), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('budget_range', sa.String(length=100), nullable=True),
        sa.Column('pain_point', sa.Text(), nullable=True),
        sa.Column('urgency', sa.String(length=20), nullable=True),
        sa.Column('lead_message', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default=sa.text("'NEW'")),
        sa.Column('score_label', sa.String(length=10), nullable=True),
        sa.Column('score_value', sa.Integer(), nullable=True),
        sa.Column('score_rationale', sa.Text(), nullable=True),
        sa.Column('recommended_action', sa.String(length=30), nullable=True),
        sa.Column('enrichment_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('processing_status', sa.String(length=20), nullable=False, server_default=sa.text("'IDLE'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_leads_status', 'leads', ['status'])
    op.create_index('ix_leads_score_label', 'leads', ['score_label'])
    op.create_index('ix_leads_created_at', 'leads', ['created_at'])

    # Create activity_logs table
    op.create_table(
        'activity_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(length=30), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_activity_logs_lead_id', 'activity_logs', ['lead_id'])

    # Create email_drafts table
    op.create_table(
        'email_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('variant', sa.String(length=30), nullable=False, server_default=sa.text("'first_touch'")),
        sa.Column('approved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_status', sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clicked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('bounced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_email_drafts_lead_id', 'email_drafts', ['lead_id'])

    # Create feedbacks table
    op.create_table(
        'feedbacks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('outcome', sa.String(length=30), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_feedbacks_lead_id', 'feedbacks', ['lead_id'])

    # Create traces table
    op.create_table(
        'traces',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('graph_run_id', sa.String(length=255), nullable=False),
        sa.Column('node_events', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('llm_inputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('llm_outputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_traces_lead_id', 'traces', ['lead_id'])

    # Create pipeline_runs table
    op.create_table(
        'pipeline_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('node_timings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_id')
    )
    op.create_index('ix_pipeline_runs_lead_id', 'pipeline_runs', ['lead_id'])

    # Create scoring_configs table
    op.create_table(
        'scoring_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('weights', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('thresholds', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('scoring_configs')
    op.drop_index('ix_pipeline_runs_lead_id', table_name='pipeline_runs')
    op.drop_table('pipeline_runs')
    op.drop_index('ix_traces_lead_id', table_name='traces')
    op.drop_table('traces')
    op.drop_index('ix_feedbacks_lead_id', table_name='feedbacks')
    op.drop_table('feedbacks')
    op.drop_index('ix_email_drafts_lead_id', table_name='email_drafts')
    op.drop_table('email_drafts')
    op.drop_index('ix_activity_logs_lead_id', table_name='activity_logs')
    op.drop_table('activity_logs')
    op.drop_index('ix_leads_created_at', table_name='leads')
    op.drop_index('ix_leads_score_label', table_name='leads')
    op.drop_index('ix_leads_status', table_name='leads')
    op.drop_table('leads')
    op.drop_table('users')
