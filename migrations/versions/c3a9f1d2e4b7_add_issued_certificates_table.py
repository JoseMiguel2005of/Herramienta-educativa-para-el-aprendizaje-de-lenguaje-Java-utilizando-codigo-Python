"""Add issued_certificates table for publicly verifiable certificates.

Revision ID: c3a9f1d2e4b7
Revises: 8b4e2f91c0d1
Create Date: 2026-11-22 13:22:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3a9f1d2e4b7"
down_revision = "8b4e2f91c0d1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "issued_certificates" not in inspector.get_table_names():
        op.create_table(
            "issued_certificates",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("section_key", sa.String(length=100), nullable=False),
            sa.Column("course_name", sa.String(length=160), nullable=False),
            sa.Column("total_lessons", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verification_code", sa.String(length=64), nullable=False),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name=op.f("fk_issued_certificates_user_id_users"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_issued_certificates")),
            sa.UniqueConstraint(
                "user_id",
                "section_key",
                name="uq_issued_certificates_user_section",
            ),
            sa.UniqueConstraint(
                "verification_code",
                name=op.f("uq_issued_certificates_verification_code"),
            ),
        )
        op.create_index(
            op.f("ix_issued_certificates_user_id"),
            "issued_certificates",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_issued_certificates_section_key"),
            "issued_certificates",
            ["section_key"],
            unique=False,
        )
        op.create_index(
            op.f("ix_issued_certificates_verification_code"),
            "issued_certificates",
            ["verification_code"],
            unique=True,
        )
        op.create_index(
            op.f("ix_issued_certificates_issued_at"),
            "issued_certificates",
            ["issued_at"],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "issued_certificates" in inspector.get_table_names():
        op.drop_table("issued_certificates")
