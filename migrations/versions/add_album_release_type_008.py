"""Add release_type field to Album table

Revision ID: add_album_release_type_008
Revises: remove_track_lyrics_007
Create Date: 2026-07-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_album_release_type_008'
down_revision = 'remove_track_lyrics_007'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('album', schema=None) as batch_op:
        batch_op.add_column(sa.Column('release_type', sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table('album', schema=None) as batch_op:
        batch_op.drop_column('release_type')
