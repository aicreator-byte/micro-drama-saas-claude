"""Add auto_generate_jobs + auto_generate_steps (Fase 1 auto-generate)

Revision ID: a7c3e9f1b824
Revises: f4a11c9d205e
Create Date: 2026-11-19

One job = 5 sequential steps (series_bible -> characters -> locations ->
episodes -> prompts). Status/step columns are plain strings; the Python
enums live in app/models/auto_generate.py.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c3e9f1b824'
down_revision: Union[str, None] = 'f4a11c9d205e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auto_generate_jobs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('genre', sa.String(length=100), nullable=True),
        sa.Column('total_episodes', sa.Integer(), nullable=False),
        sa.Column('premise', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auto_generate_jobs_project_id', 'auto_generate_jobs', ['project_id'])

    op.create_table(
        'auto_generate_steps',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('job_id', sa.Uuid(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('step', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['auto_generate_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auto_generate_steps_job_position', 'auto_generate_steps', ['job_id', 'position'])


def downgrade() -> None:
    op.drop_index('ix_auto_generate_steps_job_position', table_name='auto_generate_steps')
    op.drop_table('auto_generate_steps')
    op.drop_index('ix_auto_generate_jobs_project_id', table_name='auto_generate_jobs')
    op.drop_table('auto_generate_jobs')
