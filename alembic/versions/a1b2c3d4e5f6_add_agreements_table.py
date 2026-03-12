"""add_agreements_table

Revision ID: a1b2c3d4e5f6
Revises: 6f04865650c5
Create Date: 2026-03-06 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6f04865650c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('agreements',
        sa.Column('id', sa.String(length=30), nullable=False),
        sa.Column('status', sa.Enum('draft', 'awaiting_payment', 'awaiting_signature', 'signed', 'active', 'terminated', 'expired', name='agreement_status_enum', create_constraint=True), nullable=False),
        sa.Column('rent_amount', sa.Integer(), nullable=False),
        sa.Column('security_deposit', sa.Integer(), nullable=False),
        sa.Column('maintenance_charges', sa.Integer(), nullable=False),
        sa.Column('lease_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lease_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lease_duration_months', sa.Integer(), nullable=False),
        sa.Column('terms_text', sa.Text(), nullable=True),
        sa.Column('custom_clauses', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tenant_signature', sa.String(length=512), nullable=True),
        sa.Column('owner_signature', sa.String(length=512), nullable=True),
        sa.Column('tenant_signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('owner_signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pdf_url', sa.String(length=512), nullable=True),
        sa.Column('property_id', sa.String(length=30), nullable=False),
        sa.Column('tenant_id', sa.String(length=30), nullable=False),
        sa.Column('owner_id', sa.String(length=30), nullable=False),
        sa.Column('deposit_payment_id', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['deposit_payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agreements_owner_id'), 'agreements', ['owner_id'], unique=False)
    op.create_index(op.f('ix_agreements_property_id'), 'agreements', ['property_id'], unique=False)
    op.create_index(op.f('ix_agreements_status'), 'agreements', ['status'], unique=False)
    op.create_index(op.f('ix_agreements_tenant_id'), 'agreements', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_agreements_tenant_id'), table_name='agreements')
    op.drop_index(op.f('ix_agreements_status'), table_name='agreements')
    op.drop_index(op.f('ix_agreements_property_id'), table_name='agreements')
    op.drop_index(op.f('ix_agreements_owner_id'), table_name='agreements')
    op.drop_table('agreements')
    op.execute("DROP TYPE IF EXISTS agreement_status_enum")
