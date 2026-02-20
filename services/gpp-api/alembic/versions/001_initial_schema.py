"""Initial schema for gpp-api.

This migration creates the tables needed by gpp-api. Since the database
is shared with publicatiebank (Django), tables may already exist.
We use IF NOT EXISTS to handle both fresh installs and shared database scenarios.

Revision ID: 001_initial
Revises:
Create Date: 2026-02-06

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tables if they don't exist.

    This handles both:
    - Fresh install: creates all tables
    - Shared with publicatiebank: tables already exist, skip creation
    """
    conn = op.get_bind()

    # Check if we're in a shared database scenario (Django tables exist)
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'django_migrations')"
        )
    )
    is_shared_db = result.scalar()

    if is_shared_db:
        # Tables are managed by Django/publicatiebank, nothing to do
        # Just ensure our custom indexes exist
        pass
    else:
        # Fresh install - create all tables
        # Note: In practice, publicatiebank should be set up first
        # This branch is mainly for testing scenarios

        # metadata_organisation
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata_organisation (
                id BIGSERIAL PRIMARY KEY,
                uuid UUID NOT NULL UNIQUE,
                naam VARCHAR(200) NOT NULL,
                identifier VARCHAR(200) NOT NULL UNIQUE,
                rsin VARCHAR(9),
                is_actief BOOLEAN NOT NULL DEFAULT true,
                aangemaakt TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                gewijzigd TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )

        # metadata_informationcategory
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata_informationcategory (
                id BIGSERIAL PRIMARY KEY,
                uuid UUID NOT NULL UNIQUE,
                naam VARCHAR(80) NOT NULL,
                naam_meervoud VARCHAR(80) NOT NULL,
                definitie TEXT NOT NULL,
                oorsprong VARCHAR(200),
                order_index INTEGER NOT NULL DEFAULT 0,
                aangemaakt TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                gewijzigd TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )

        # metadata_theme (topics)
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata_theme (
                id BIGSERIAL PRIMARY KEY,
                uuid UUID NOT NULL UNIQUE,
                naam VARCHAR(80) NOT NULL,
                identifier VARCHAR(200) NOT NULL UNIQUE,
                parent_id BIGINT REFERENCES metadata_theme(id) ON DELETE CASCADE,
                order_index INTEGER NOT NULL DEFAULT 0,
                aangemaakt TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                gewijzigd TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )

        # accounts_organisationunit
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts_organisationunit (
                id BIGSERIAL PRIMARY KEY,
                uuid UUID NOT NULL UNIQUE,
                identifier VARCHAR(200) NOT NULL UNIQUE,
                naam VARCHAR(200) NOT NULL,
                aangemaakt TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                gewijzigd TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )

        # accounts_organisationmember
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts_organisationmember (
                id BIGSERIAL PRIMARY KEY,
                uuid UUID NOT NULL UNIQUE,
                identifier VARCHAR(200) NOT NULL UNIQUE,
                naam VARCHAR(200) NOT NULL,
                aangemaakt TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                gewijzigd TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )

        # publications_publication
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS publications_publication (
                id BIGSERIAL PRIMARY KEY,
                uuid UUID NOT NULL UNIQUE,
                officiele_titel VARCHAR(1000) NOT NULL,
                verkorte_titel VARCHAR(200),
                omschrijving TEXT,
                publicatiestatus VARCHAR(20) NOT NULL DEFAULT 'concept',
                registratiedatum TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                laatst_gewijzigd_datum TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                gepubliceerd_op TIMESTAMP WITH TIME ZONE,
                ingetrokken_op TIMESTAMP WITH TIME ZONE,
                datum_begin_geldigheid DATE,
                datum_einde_geldigheid DATE,
                publisher_id BIGINT REFERENCES metadata_organisation(id) ON DELETE SET NULL,
                verantwoordelijke_id BIGINT REFERENCES metadata_organisation(id) ON DELETE SET NULL,
                opsteller_id BIGINT REFERENCES metadata_organisation(id) ON DELETE SET NULL,
                eigenaar_id BIGINT REFERENCES accounts_organisationmember(id) ON DELETE SET NULL,
                eigenaar_groep_id BIGINT REFERENCES accounts_organisationunit(id) ON DELETE SET NULL,
                aangemaakt TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                gewijzigd TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )

        # publications_publication_informatie_categorieen (M2M)
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS publications_publication_informatie_categorieen (
                id BIGSERIAL PRIMARY KEY,
                publication_id BIGINT NOT NULL REFERENCES publications_publication(id) ON DELETE CASCADE,
                informationcategory_id BIGINT NOT NULL REFERENCES metadata_informationcategory(id) ON DELETE CASCADE,
                UNIQUE(publication_id, informationcategory_id)
            )
            """
        )

        # publications_publication_onderwerpen (M2M)
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS publications_publication_onderwerpen (
                id BIGSERIAL PRIMARY KEY,
                publication_id BIGINT NOT NULL REFERENCES publications_publication(id) ON DELETE CASCADE,
                theme_id BIGINT NOT NULL REFERENCES metadata_theme(id) ON DELETE CASCADE,
                UNIQUE(publication_id, theme_id)
            )
            """
        )

        # publications_publicationidentifier
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS publications_publicationidentifier (
                id BIGSERIAL PRIMARY KEY,
                publicatie_id BIGINT NOT NULL REFERENCES publications_publication(id) ON DELETE CASCADE,
                kenmerk VARCHAR(255) NOT NULL,
                bron VARCHAR(100) NOT NULL,
                CONSTRAINT no_duplicate_publication_identifiers UNIQUE(publicatie_id, kenmerk, bron)
            )
            """
        )

        # publications_document
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS publications_document (
                id BIGSERIAL PRIMARY KEY,
                uuid UUID NOT NULL UNIQUE,
                publicatie_id BIGINT NOT NULL REFERENCES publications_publication(id) ON DELETE CASCADE,
                identifier VARCHAR(100),
                officiele_titel VARCHAR(1000),
                verkorte_titel VARCHAR(200),
                omschrijving TEXT,
                publicatiestatus VARCHAR(20) NOT NULL DEFAULT 'concept',
                creatiedatum DATE,
                ontvangstdatum TIMESTAMP WITH TIME ZONE,
                datum_ondertekend TIMESTAMP WITH TIME ZONE,
                bestandsnaam VARCHAR(200),
                bestandsformaat VARCHAR(100),
                bestandsomvang BIGINT,
                document_uuid VARCHAR(100),
                document_service_id BIGINT,
                lock VARCHAR(100),
                upload_complete BOOLEAN NOT NULL DEFAULT false,
                metadata_gestript_op TIMESTAMP WITH TIME ZONE,
                registratiedatum TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                laatst_gewijzigd_datum TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                aangemaakt TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                gewijzigd TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )

        # publications_documentidentifier
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS publications_documentidentifier (
                id BIGSERIAL PRIMARY KEY,
                document_id BIGINT NOT NULL REFERENCES publications_document(id) ON DELETE CASCADE,
                kenmerk VARCHAR(255) NOT NULL,
                bron VARCHAR(100) NOT NULL,
                CONSTRAINT no_duplicate_document_identifiers UNIQUE(document_id, kenmerk, bron)
            )
            """
        )


def downgrade() -> None:
    """Drop tables in reverse order.

    WARNING: This will delete all data!
    Only use in development/testing.
    """
    conn = op.get_bind()

    # Check if Django manages these tables
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'django_migrations')"
        )
    )
    is_shared_db = result.scalar()

    if is_shared_db:
        # Don't drop tables managed by Django
        pass
    else:
        # Drop in reverse dependency order
        op.execute("DROP TABLE IF EXISTS publications_documentidentifier CASCADE")
        op.execute("DROP TABLE IF EXISTS publications_document CASCADE")
        op.execute("DROP TABLE IF EXISTS publications_publicationidentifier CASCADE")
        op.execute("DROP TABLE IF EXISTS publications_publication_onderwerpen CASCADE")
        op.execute("DROP TABLE IF EXISTS publications_publication_informatie_categorieen CASCADE")
        op.execute("DROP TABLE IF EXISTS publications_publication CASCADE")
        op.execute("DROP TABLE IF EXISTS accounts_organisationmember CASCADE")
        op.execute("DROP TABLE IF EXISTS accounts_organisationunit CASCADE")
        op.execute("DROP TABLE IF EXISTS metadata_theme CASCADE")
        op.execute("DROP TABLE IF EXISTS metadata_informationcategory CASCADE")
        op.execute("DROP TABLE IF EXISTS metadata_organisation CASCADE")
