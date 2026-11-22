"""Drop unused achievements table

Revision ID: 8b4e2f91c0d1
Revises: 2255d98a99d3
Create Date: 2026-11-22 12:42:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8b4e2f91c0d1'
down_revision = '2255d98a99d3'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'achievements' in inspector.get_table_names():
        op.drop_table('achievements')


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'achievements' not in inspector.get_table_names():
        op.create_table(
            'achievements',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('badge_id', sa.String(length=100), nullable=False),
            sa.Column('unlocked_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_achievements_user_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_achievements')),
            sa.UniqueConstraint('user_id', 'badge_id', name='uq_achievements_user_badge'),
        )
        with op.batch_alter_table('achievements', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_achievements_badge_id'), ['badge_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_achievements_user_id'), ['user_id'], unique=False)
