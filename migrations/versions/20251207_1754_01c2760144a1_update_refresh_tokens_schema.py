"""update_refresh_tokens_schema

Revision ID: 01c2760144a1
Revises: add_is_admin_field
Create Date: 2025-12-07 17:54:49.827241+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '01c2760144a1'
down_revision = 'add_is_admin_field'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename column 'token' to 'token_hash'
    op.alter_column('refresh_tokens', 'token', new_column_name='token_hash')
    
    # Add new columns
    op.add_column('refresh_tokens', sa.Column('device_info', sa.String(255), nullable=True))
    op.add_column('refresh_tokens', sa.Column('ip_address', sa.String(45), nullable=True))
    op.add_column('refresh_tokens', sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('refresh_tokens', sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create new index on token_hash
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)
    
    # Drop old index on token
    op.drop_index('ix_refresh_tokens_token', table_name='refresh_tokens')


def downgrade() -> None:
    # Restore old index
    op.create_index('ix_refresh_tokens_token', 'refresh_tokens', ['token_hash'], unique=True)
    
    # Drop new index
    op.drop_index('ix_refresh_tokens_token_hash', table_name='refresh_tokens')
    
    # Drop new columns
    op.drop_column('refresh_tokens', 'revoked_at')
    op.drop_column('refresh_tokens', 'is_revoked')
    op.drop_column('refresh_tokens', 'ip_address')
    op.drop_column('refresh_tokens', 'device_info')
    
    # Rename column back
    op.alter_column('refresh_tokens', 'token_hash', new_column_name='token')

