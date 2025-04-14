"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-04-14 09:10:00.000000

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
    # Create search_results table
    op.create_table('search_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('domain', sa.String(), nullable=False),
        sa.Column('company_name', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('region', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('query', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('result_url', sa.String(length=2048), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=True),
        sa.Column('snippet', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table('search_results') 