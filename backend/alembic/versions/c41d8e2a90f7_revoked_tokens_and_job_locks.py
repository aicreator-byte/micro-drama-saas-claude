"""Add revoked_tokens table + auto_generate_jobs lock columns (round 2)

Revision ID: c41d8e2a90f7
Revises: a7c3e9f1b824
Create Date: 2026-11-20

- revoked_tokens: denylist for logout (token revocation); rows are
  keyed by JWT jti and deleted opportunistically past expiry.
- auto_generate_jobs.locked_by / locked_at / lease_expires_at:
  multi-worker job lock (claim = one atomic UPDATE, lease renewed by
  a heartbeat while the job runs).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c41d8e2a90f7'
down_revision: Union[str, None] = 'a7c3e9f1b824'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'revoked_tokens',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('jti', sa.String(length=64), nullable=False),
        sa.Column('token_type', sa.String(length=20), nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti'),
    )
    op.create_index('ix_revoked_tokens_jti', 'revoked_tokens', ['jti'])

    op.add_column('auto_generate_jobs', sa.Column('locked_by', sa.String(length=64), nullable=True))
    op.add_column('auto_generate_jobs', sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('auto_generate_jobs', sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_auto_generate_jobs_lease_expires_at', 'auto_generate_jobs', ['lease_expires_at'])


def downgrade() -> None:
    op.drop_index('ix_auto_generate_jobs_lease_expires_at', table_name='auto_generate_jobs')
    op.drop_column('auto_generate_jobs', 'lease_expires_at')
    op.drop_column('auto_generate_jobs', 'locked_at')
    op.drop_column('auto_generate_jobs', 'locked_by')
    op.drop_index('ix_revoked_tokens_jti', table_name='revoked_tokens')
    op.drop_table('revoked_tokens')
