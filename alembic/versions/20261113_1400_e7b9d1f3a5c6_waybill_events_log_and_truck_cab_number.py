"""waybill log, events log (officer notes) and the truck cab number

Revision ID: e7b9d1f3a5c6
Revises: d6a8c0e2f4b5
Create Date: 2026-11-13 14:00:00

Adds two tables, `waybill_entries` (couriers bringing goods) and `occurrences` (the Events log:
an officer's own notes), and an optional `cab_number` on `trucks` and `truck_entries`. Nothing
existing is changed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e7b9d1f3a5c6'
down_revision: Union[str, None] = 'd6a8c0e2f4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('occurrences',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('facility_id', sa.Uuid(), nullable=False),
    sa.Column('officer_id', sa.Uuid(), nullable=False),
    sa.Column('gate', sa.SmallInteger(), nullable=True),
    sa.Column('note', sa.String(length=2000), nullable=False),
    sa.Column('logged_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('signature', sa.LargeBinary(), nullable=True),
    sa.Column('signature_reused', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('device_id', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_occurrences_facility_id_facilities'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['officer_id'], ['officers.id'], name=op.f('fk_occurrences_officer_id_officers'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_occurrences'))
    )
    op.create_index('ix_occurrences_facility_logged_at', 'occurrences', ['facility_id', 'logged_at'], unique=False)
    op.create_index('ix_occurrences_facility_updated', 'occurrences', ['facility_id', 'updated_at'], unique=False)
    op.create_table('waybill_entries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('full_name', sa.String(length=150), nullable=False),
    sa.Column('phone', sa.String(length=32), nullable=True),
    sa.Column('items', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('came_by_vehicle', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('plate_number', sa.String(length=20), nullable=True),
    sa.Column('facility_id', sa.Uuid(), nullable=False),
    sa.Column('signed_in_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('signed_out_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('signature_in', sa.LargeBinary(), nullable=True),
    sa.Column('signature_out', sa.LargeBinary(), nullable=True),
    sa.Column('signature_in_reused', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('signature_out_reused', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('signed_in_by', sa.Uuid(), nullable=False),
    sa.Column('signed_out_by', sa.Uuid(), nullable=True),
    sa.Column('device_id', sa.String(length=64), nullable=True),
    sa.Column('gate_in', sa.SmallInteger(), nullable=True),
    sa.Column('gate_out', sa.SmallInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('came_by_vehicle OR plate_number IS NULL', name=op.f('ck_waybill_entries_waybill_plate_needs_vehicle')),
    sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_waybill_entries_facility_id_facilities'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['signed_in_by'], ['officers.id'], name=op.f('fk_waybill_entries_signed_in_by_officers'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['signed_out_by'], ['officers.id'], name=op.f('fk_waybill_entries_signed_out_by_officers'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_waybill_entries'))
    )
    op.create_index('ix_waybill_entries_facility_phone', 'waybill_entries', ['facility_id', 'phone'], unique=False)
    op.create_index('ix_waybill_entries_facility_signed_in', 'waybill_entries', ['facility_id', 'signed_in_at'], unique=False)
    op.create_index('ix_waybill_entries_facility_updated', 'waybill_entries', ['facility_id', 'updated_at'], unique=False)
    op.create_index('ix_waybill_entries_open', 'waybill_entries', ['facility_id'], unique=False, postgresql_where=sa.text('signed_out_at IS NULL'))
    op.add_column('truck_entries', sa.Column('cab_number', sa.String(length=20), nullable=True))
    op.add_column('trucks', sa.Column('cab_number', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('trucks', 'cab_number')
    op.drop_column('truck_entries', 'cab_number')
    op.drop_index('ix_waybill_entries_open', table_name='waybill_entries', postgresql_where=sa.text('signed_out_at IS NULL'))
    op.drop_index('ix_waybill_entries_facility_updated', table_name='waybill_entries')
    op.drop_index('ix_waybill_entries_facility_signed_in', table_name='waybill_entries')
    op.drop_index('ix_waybill_entries_facility_phone', table_name='waybill_entries')
    op.drop_table('waybill_entries')
    op.drop_index('ix_occurrences_facility_updated', table_name='occurrences')
    op.drop_index('ix_occurrences_facility_logged_at', table_name='occurrences')
    op.drop_table('occurrences')
