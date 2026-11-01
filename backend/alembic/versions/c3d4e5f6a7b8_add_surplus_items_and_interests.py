"""Add surplus_items and surplus_interests tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-01 20:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. surplus_items table
    op.create_table(
        'surplus_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit', sa.String(length=20), server_default='units', nullable=False),
        sa.Column('condition', sa.String(length=20), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('storage_details', sa.String(length=200), nullable=True),
        sa.Column('contact_note', sa.String(length=200), nullable=True),
        sa.Column('image_path', sa.String(length=255), nullable=True),
        sa.Column('part_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='AVAILABLE', nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name='fk_surplus_items_location_id', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['part_id'], ['spare_parts.id'], name='fk_surplus_items_part_id', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_surplus_items_created_by', ondelete='RESTRICT'),
        sa.CheckConstraint("kind IN ('SPARE_PART', 'MATERIAL', 'MACHINERY')", name='ck_surplus_items_kind'),
        sa.CheckConstraint('quantity >= 0', name='ck_surplus_items_quantity'),
        sa.CheckConstraint("condition IN ('NEW', 'GOOD', 'USED', 'NEEDS_REPAIR')", name='ck_surplus_items_condition'),
        sa.CheckConstraint("status IN ('AVAILABLE', 'RESERVED', 'CLAIMED', 'WITHDRAWN')", name='ck_surplus_items_status'),
        sa.PrimaryKeyConstraint('id', name='pk_surplus_items')
    )
    op.create_index('ix_surplus_items_status_location_id', 'surplus_items', ['status', 'location_id'])
    op.create_index('ix_surplus_items_kind', 'surplus_items', ['kind'])
    op.create_index('ix_surplus_items_created_at', 'surplus_items', ['created_at'])
    op.create_index('ix_surplus_items_location_id', 'surplus_items', ['location_id'])
    op.create_index('ix_surplus_items_part_id', 'surplus_items', ['part_id'])

    # 2. surplus_interests table
    op.create_table(
        'surplus_interests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('quantity_requested', sa.Integer(), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['surplus_items.id'], name='fk_surplus_interests_item_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_surplus_interests_user_id', ondelete='RESTRICT'),
        sa.CheckConstraint('quantity_requested >= 1', name='ck_surplus_interests_quantity_requested'),
        sa.UniqueConstraint('item_id', 'user_id', name='uq_surplus_interests_item_user'),
        sa.PrimaryKeyConstraint('id', name='pk_surplus_interests')
    )
    op.create_index('ix_surplus_interests_item_id', 'surplus_interests', ['item_id'])
    op.create_index('ix_surplus_interests_user_id', 'surplus_interests', ['user_id'])

    # 3. notifications nullable surplus_item_id column
    op.add_column(
        'notifications',
        sa.Column('surplus_item_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_notifications_surplus_item_id',
        'notifications',
        'surplus_items',
        ['surplus_item_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_notifications_surplus_item_id', 'notifications', ['surplus_item_id'])


def downgrade() -> None:
    op.drop_index('ix_notifications_surplus_item_id', table_name='notifications')
    op.drop_constraint('fk_notifications_surplus_item_id', 'notifications', type_='foreignkey')
    op.drop_column('notifications', 'surplus_item_id')

    op.drop_index('ix_surplus_interests_user_id', table_name='surplus_interests')
    op.drop_index('ix_surplus_interests_item_id', table_name='surplus_interests')
    op.drop_table('surplus_interests')

    op.drop_index('ix_surplus_items_part_id', table_name='surplus_items')
    op.drop_index('ix_surplus_items_location_id', table_name='surplus_items')
    op.drop_index('ix_surplus_items_created_at', table_name='surplus_items')
    op.drop_index('ix_surplus_items_kind', table_name='surplus_items')
    op.drop_index('ix_surplus_items_status_location_id', table_name='surplus_items')
    op.drop_table('surplus_items')

