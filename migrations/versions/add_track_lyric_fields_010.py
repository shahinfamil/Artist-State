"""Add lyricist and lyrics fields to Track table

Revision ID: add_track_lyric_fields_010
Revises: add_track_has_music_video_009
Create Date: 2026-08-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_track_lyric_fields_010'
down_revision = 'add_track_has_music_video_009'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.add_column(sa.Column('lyricist', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('lyrics', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.drop_column('lyrics')
        batch_op.drop_column('lyricist')
