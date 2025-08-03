"""Add comprehensive API request logging tables

Revision ID: 001
Revises: 
Create Date: 2025-08-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create api_request_logs table
    op.create_table('api_request_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('path', sa.String(length=200), nullable=False),
        sa.Column('query_params', sa.Text(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('event_type', sa.String(length=20), nullable=False),
        sa.Column('request_size_bytes', sa.Integer(), nullable=True),
        sa.Column('response_size_bytes', sa.Integer(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('rag_query', sa.Text(), nullable=True),
        sa.Column('rag_context_used', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rag_response_length', sa.Integer(), nullable=True),
        sa.Column('chat_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_timestamp', 'api_request_logs', ['timestamp'])
    op.create_index('idx_endpoint_timestamp', 'api_request_logs', ['path', 'timestamp'])
    op.create_index('idx_user_timestamp', 'api_request_logs', ['user_id', 'timestamp'])
    op.create_index('idx_event_type', 'api_request_logs', ['event_type'])
    op.create_index('idx_status_timestamp', 'api_request_logs', ['status_code', 'timestamp'])
    
    # Create daily_metrics table
    op.create_table('daily_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=True),
        sa.Column('unique_users', sa.Integer(), nullable=True),
        sa.Column('avg_response_time_ms', sa.Float(), nullable=True),
        sa.Column('error_rate', sa.Float(), nullable=True),
        sa.Column('endpoint_stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('generate_stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    
    # Create index for daily_metrics
    op.create_index('idx_date', 'daily_metrics', ['date'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_date', table_name='daily_metrics')
    op.drop_index('idx_status_timestamp', table_name='api_request_logs')
    op.drop_index('idx_event_type', table_name='api_request_logs')
    op.drop_index('idx_user_timestamp', table_name='api_request_logs')
    op.drop_index('idx_endpoint_timestamp', table_name='api_request_logs')
    op.drop_index('idx_timestamp', table_name='api_request_logs')
    
    # Drop tables
    op.drop_table('daily_metrics')
    op.drop_table('api_request_logs')
