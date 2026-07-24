"""Create dedicated table for artist wikipedia data

Revision ID: 5f7109f3294a
Revises: add_wikipedia_fields_004
Create Date: 2026-07-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column, text


# revision identifiers, used by Alembic.
revision = '5f7109f3294a'
down_revision = 'add_wikipedia_fields_004'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'artist_wikipedia_data' not in inspector.get_table_names():
        op.create_table(
            'artist_wikipedia_data',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('artist_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=300), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
                sa.Column('timeline_section', sa.Text(), nullable=True),
            sa.Column('infobox_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('artist_id'),
        )

    if 'site_media' not in inspector.get_table_names():
        op.create_table(
            'site_media',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('type', sa.String(length=20), nullable=False),
            sa.Column('url', sa.String(length=500), nullable=False),
            sa.Column('label', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'artist' in inspector.get_table_names():
        artist_columns = {col['name'] for col in inspector.get_columns('artist')}
        if {'wikipedia_title', 'wikipedia_image_url', 'wikipedia_infobox_json'} <= artist_columns:
            rows = conn.execute(text('SELECT id, wikipedia_title, wikipedia_image_url, wikipedia_infobox_json FROM artist')).fetchall()
            for row in rows:
                existing = conn.execute(text('SELECT 1 FROM artist_wikipedia_data WHERE artist_id = :artist_id'), {'artist_id': row[0]}).fetchone()
                if existing is None:
                    conn.execute(
                        text(
                            "INSERT INTO artist_wikipedia_data (artist_id, title, image_url, infobox_json, created_at, updated_at) VALUES (:artist_id, :title, :image_url, :infobox_json, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                        ),
                        {
                            'artist_id': row[0],
                            'title': row[1],
                            'image_url': row[2],
                            'infobox_json': row[3],
                        }
                    )
