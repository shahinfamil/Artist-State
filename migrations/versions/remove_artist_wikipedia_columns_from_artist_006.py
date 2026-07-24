"""Remove legacy Wikipedia columns from artist table

Revision ID: remove_artist_wikipedia_columns_from_artist_006
Revises: remove_instagram_followers_list_005
Create Date: 2026-07-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_artist_wikipedia_columns_from_artist_006'
down_revision = 'remove_instagram_followers_list_005'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'artist' in inspector.get_table_names():
        artist_columns = {col['name'] for col in inspector.get_columns('artist')}
        with op.batch_alter_table('artist', schema=None) as batch_op:
            if 'wikipedia_title' in artist_columns:
                batch_op.drop_column('wikipedia_title')
            if 'wikipedia_page_url' in artist_columns:
                batch_op.drop_column('wikipedia_page_url')
            if 'wikipedia_image_url' in artist_columns:
                batch_op.drop_column('wikipedia_image_url')
            if 'wikipedia_infobox_json' in artist_columns:
                batch_op.drop_column('wikipedia_infobox_json')


def downgrade():
    with op.batch_alter_table('artist', schema=None) as batch_op:
        batch_op.add_column(sa.Column('wikipedia_infobox_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('wikipedia_image_url', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('wikipedia_page_url', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('wikipedia_title', sa.String(length=300), nullable=True))
