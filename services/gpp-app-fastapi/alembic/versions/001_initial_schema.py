"""Initial schema for gpp-app-fastapi.

Creates the user groups tables for managing access control.

Revision ID: 001_initial
Revises:
Create Date: 2026-02-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user groups tables."""
    # gebruikersgroep - main user group table
    op.create_table(
        "gebruikersgroep",
        sa.Column("uuid", UUID(as_uuid=True), primary_key=True),
        sa.Column("naam", sa.String(255), unique=True, nullable=False),
        sa.Column("omschrijving", sa.Text, nullable=True),
    )
    op.create_index("ix_gebruikersgroep_uuid", "gebruikersgroep", ["uuid"])

    # gebruikersgroep_waardelijst - junction table for group-waardelijst
    op.create_table(
        "gebruikersgroep_waardelijst",
        sa.Column(
            "gebruikersgroep_uuid",
            UUID(as_uuid=True),
            sa.ForeignKey("gebruikersgroep.uuid", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("waardelijst_id", sa.String(255), primary_key=True),
    )

    # gebruikersgroep_gebruiker - junction table for group-user
    op.create_table(
        "gebruikersgroep_gebruiker",
        sa.Column(
            "gebruikersgroep_uuid",
            UUID(as_uuid=True),
            sa.ForeignKey("gebruikersgroep.uuid", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("gebruiker_id", sa.String(255), primary_key=True),
    )


def downgrade() -> None:
    """Drop user groups tables."""
    op.drop_table("gebruikersgroep_gebruiker")
    op.drop_table("gebruikersgroep_waardelijst")
    op.drop_table("gebruikersgroep")
