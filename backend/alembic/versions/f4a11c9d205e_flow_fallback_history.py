"""Add flow_bridge.fallback_history (Google account fallback audit trail)

Revision ID: f4a11c9d205e
Revises: b3f8a1c9d204
Create Date: 2026-11-17

Stores the per-account fallback attempts for a Flow task as a JSON array
(each {"account_id", "email", "outcome", "reason", "detail"}), so the task
records which Google account was actually used and why the others were
skipped. Written by app/services/flow_account_fallback.py.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a11c9d205e'
down_revision: Union[str, None] = 'b3f8a1c9d204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('flow_bridge', sa.Column('fallback_history', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('flow_bridge', 'fallback_history')
