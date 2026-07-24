"""Add release_date field to Track table

Revision ID: add_track_release_date_003
Revises: add_artist_name_002
Create Date: 2026-06-29 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_track_release_date_003'
down_revision = 'add_artist_name_002'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.add_column(sa.Column('release_date', sa.Date(), nullable=True))

    op.execute("""
        UPDATE track
        SET release_date = (
            SELECT album.release_date
            FROM album
            WHERE album.id = track.album_id
        )
        WHERE release_date IS NULL
          AND EXISTS (
              SELECT 1
              FROM album
              WHERE album.id = track.album_id
                AND album.release_date IS NOT NULL
          )
    """)


def downgrade():
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.drop_column('release_date')
