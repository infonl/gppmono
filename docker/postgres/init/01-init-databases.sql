-- Initialize all databases for GPP services
-- This script runs on first startup of the PostgreSQL container

-- ODPC (GPP-app)
CREATE DATABASE "ODPC";

-- WOO Publications (GPP-publicatiebank)
CREATE USER woo_publications;
CREATE DATABASE woo_publications WITH OWNER woo_publications;

-- OpenZaak (Document Management)
CREATE USER openzaak;
CREATE DATABASE openzaak WITH OWNER openzaak;
