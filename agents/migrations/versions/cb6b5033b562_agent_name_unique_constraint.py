"""agent_name unique constraint

Revision ID: cb6b5033b562
Revises: a8eefcfe5e74
Create Date: 2026-09-14 10:10:12.131643

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb6b5033b562'
down_revision: Union[str, None] = 'a8eefcfe5e74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_agents_agent_name', 'agents', ['agent_name'])


def downgrade() -> None:
    op.drop_constraint('uq_agents_agent_name', 'agents', type_='unique')
