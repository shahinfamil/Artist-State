"""remove track lyrics

Revision ID: remove_track_lyrics_007
Revises: remove_artist_wikipedia_columns_from_artist_006
Create Date: 2026-07-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_track_lyrics_007'
down_revision = 'remove_artist_wikipedia_columns_from_artist_006'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.drop_column('lyrics_lrc')


def downgrade():
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.add_column(sa.Column('lyrics_lrc', sa.Text(), nullable=True))
