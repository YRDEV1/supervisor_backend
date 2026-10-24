"""agent_name length and supervisor_id index

Revision ID: d3f1a6c8b2e4
Revises: cb6b5033b562
Create Date: 2026-10-23 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f1a6c8b2e4'
down_revision: Union[str, None] = 'cb6b5033b562'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('agents', 'agent_name', existing_type=sa.String(), type_=sa.String(length=100), existing_nullable=False)
    op.create_index('ix_agents_supervisor_id', 'agents', ['supervisor_id'])


def downgrade() -> None:
    op.drop_index('ix_agents_supervisor_id', table_name='agents')
    op.alter_column('agents', 'agent_name', existing_type=sa.String(length=100), type_=sa.String(), existing_nullable=False)
