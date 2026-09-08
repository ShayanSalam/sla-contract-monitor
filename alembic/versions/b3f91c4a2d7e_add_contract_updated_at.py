"""add updated_at to contracts

Revision ID: b3f91c4a2d7e
Revises: 80e7b42de7c1
Create Date: 2026-09-08

Adds a real updated_at column so the dashboard can show how long the
*current* extraction attempt has been running, instead of confusingly
measuring time since the contract was first uploaded (which was wrong
whenever a contract had been retried more than once).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3f91c4a2d7e'
down_revision = '80e7b42de7c1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('contracts', sa.Column('updated_at', sa.DateTime(), nullable=True))
    # Backfill existing rows so updated_at is never null for old data
    op.execute('UPDATE contracts SET updated_at = created_at WHERE updated_at IS NULL')


def downgrade():
    op.drop_column('contracts', 'updated_at')
