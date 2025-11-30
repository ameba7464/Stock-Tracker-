"""Add wb_api_key and google_sheet_id to users table

Revision ID: add_api_key_fields
Revises: 
Create Date: 2025-11-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_api_key_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавление полей для WB API ключа и Google Sheet ID."""
    # Добавляем поле wb_api_key
    op.add_column('users', sa.Column('wb_api_key', sa.String(length=500), nullable=True))
    
    # Добавляем поле google_sheet_id
    op.add_column('users', sa.Column('google_sheet_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Откат изменений."""
    op.drop_column('users', 'google_sheet_id')
    op.drop_column('users', 'wb_api_key')
