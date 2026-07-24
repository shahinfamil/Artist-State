"""Add has_music_video flag to Track table

Revision ID: add_track_has_music_video_009
Revises: add_album_release_type_008
Create Date: 2026-07-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_track_has_music_video_009'
down_revision = 'add_album_release_type_008'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.add_column(sa.Column('youtube_url_is_music_video', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('youtube_url_secondary_is_music_video', sa.Boolean(), nullable=False, server_default=sa.text('0')))


def downgrade():
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.drop_column('youtube_url_secondary_is_music_video')
        batch_op.drop_column('youtube_url_is_music_video')
