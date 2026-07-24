"""Add artist_name columns to Album and Track tables

Revision ID: add_artist_name_002
Revises: add_release_date_001
Create Date: 2026-06-29 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_artist_name_002'
down_revision = 'add_release_date_001'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('album', schema=None) as batch_op:
        batch_op.add_column(sa.Column('artist_name', sa.String(length=200), nullable=True))

    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.add_column(sa.Column('artist_name', sa.String(length=200), nullable=True))


def downgrade():
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.drop_column('artist_name')

    with op.batch_alter_table('album', schema=None) as batch_op:
        batch_op.drop_column('artist_name')
