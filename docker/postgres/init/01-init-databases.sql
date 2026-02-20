-- Initialize all databases for GPP services
-- This script runs on first startup of the PostgreSQL container

-- ODPC (GPP-app) - Legacy C#/.NET service
CREATE DATABASE "ODPC";

-- WOO Publications (GPP-publicatiebank) - Legacy Django service
CREATE USER woo_publications;
CREATE DATABASE woo_publications WITH OWNER woo_publications;

-- OpenZaak (Document Management)
CREATE USER openzaak;
CREATE DATABASE openzaak WITH OWNER openzaak;

-- GPP-API (New FastAPI backend) - Replaces publicatiebank
CREATE DATABASE gpp_api;

-- GPP-APP-FASTAPI (New FastAPI BFF) - Replaces ODPC
CREATE DATABASE gpp_app_fastapi;
