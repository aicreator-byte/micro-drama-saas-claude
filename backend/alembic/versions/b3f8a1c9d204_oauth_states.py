"""Add oauth_states table (DB-backed OAuth state, audit ronde 2 P1-19)

Revision ID: b3f8a1c9d204
Revises: 96117fdda23d
Create Date: 2026-11-17

Replaces the in-memory OAuth state dict: states are now persisted,
single-use, TTL-bound (10 minutes) and carry the redirect_uri used at
/oauth/start so the callback uses exactly the same URI.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f8a1c9d204'
down_revision: Union[str, None] = '96117fdda23d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('oauth_states',
    sa.Column('state', sa.String(length=255), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('redirect_uri', sa.String(length=2048), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('state')
    )
    op.create_index(op.f('ix_oauth_states_user_id'), 'oauth_states', ['user_id'], unique=False)
    op.create_index('ix_oauth_states_expires_at', 'oauth_states', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_oauth_states_expires_at', table_name='oauth_states')
    op.drop_index(op.f('ix_oauth_states_user_id'), table_name='oauth_states')
    op.drop_table('oauth_states')
