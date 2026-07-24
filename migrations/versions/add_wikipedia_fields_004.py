"""Add Wikipedia fields to Artist table

Revision ID: add_wikipedia_fields_004
Revises: add_track_release_date_003
Create Date: 2026-07-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_wikipedia_fields_004'
down_revision = 'add_track_release_date_003'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('artist', schema=None) as batch_op:
        batch_op.add_column(sa.Column('wikipedia_title', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('wikipedia_page_url', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('wikipedia_image_url', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('wikipedia_infobox_json', sa.Text(), nullable=True))

    with op.batch_alter_table('artist_wikipedia_data', schema=None) as batch_op:
        batch_op.add_column(sa.Column('instagram_followers_list', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('artist_wikipedia_data', schema=None) as batch_op:
        batch_op.drop_column('instagram_followers_list')

    with op.batch_alter_table('artist', schema=None) as batch_op:
        batch_op.drop_column('wikipedia_infobox_json')
        batch_op.drop_column('wikipedia_image_url')
        batch_op.drop_column('wikipedia_page_url')
        batch_op.drop_column('wikipedia_title')
