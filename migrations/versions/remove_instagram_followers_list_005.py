"""Remove instagram_followers_list from ArtistWikipediaData

Revision ID: remove_instagram_followers_list_005
Revises: add_wikipedia_fields_004
Create Date: 2026-07-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_instagram_followers_list_005'
down_revision = 'add_wikipedia_fields_004'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('artist_wikipedia_data', schema=None) as batch_op:
        batch_op.drop_column('instagram_followers_list')


def downgrade():
    with op.batch_alter_table('artist_wikipedia_data', schema=None) as batch_op:
        batch_op.add_column(sa.Column('instagram_followers_list', sa.Text(), nullable=True))
