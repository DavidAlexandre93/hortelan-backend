"""Create the initial relational schema.

Revision ID: 001_initial_schema
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return inspector.has_table(table_name)


def upgrade() -> None:
    if not _has_table('telemetry_readings'):
        op.create_table(
            'telemetry_readings',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('device_id', sa.String(length=128), nullable=False),
            sa.Column('moisture', sa.Float(), nullable=False),
            sa.Column('temperature', sa.Float(), nullable=False),
            sa.Column('ph', sa.Float(), nullable=False),
            sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('metadata', sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_telemetry_readings_device_id', 'telemetry_readings', ['device_id'])
        op.create_index(
            'ix_telemetry_device_captured_desc',
            'telemetry_readings',
            ['device_id', 'captured_at'],
        )
        op.create_index('ix_telemetry_captured_desc', 'telemetry_readings', ['captured_at'])

    if not _has_table('idempotency_records'):
        op.create_table(
            'idempotency_records',
            sa.Column('key', sa.String(length=128), nullable=False),
            sa.Column('operation', sa.String(length=128), nullable=False),
            sa.Column('fingerprint', sa.String(length=64), nullable=False),
            sa.Column('state', sa.String(length=16), nullable=False),
            sa.Column('response_json', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('key'),
        )

    if not _has_table('outbox_events'):
        op.create_table(
            'outbox_events',
            sa.Column('event_id', sa.String(length=32), nullable=False),
            sa.Column('event_type', sa.String(length=128), nullable=False),
            sa.Column('aggregate_id', sa.String(length=128), nullable=False),
            sa.Column('payload', sa.JSON(), nullable=False),
            sa.Column('state', sa.String(length=16), nullable=False),
            sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('attempt_count', sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint('event_id'),
        )
        op.create_index('ix_outbox_events_aggregate_id', 'outbox_events', ['aggregate_id'])
        op.create_index('ix_outbox_events_state', 'outbox_events', ['state'])


def downgrade() -> None:
    op.drop_table('outbox_events')
    op.drop_table('idempotency_records')
    op.drop_table('telemetry_readings')
