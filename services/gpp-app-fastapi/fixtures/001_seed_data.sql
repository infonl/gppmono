-- Seed data for gpp_app_fastapi local development
-- This file is loaded via docker-compose or manually

-- Create tables if not exists (in case migrations haven't run)
CREATE TABLE IF NOT EXISTS gebruikersgroep (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    naam VARCHAR(255) UNIQUE NOT NULL,
    omschrijving TEXT
);

CREATE TABLE IF NOT EXISTS gebruikersgroep_waardelijst (
    gebruikersgroep_uuid UUID NOT NULL REFERENCES gebruikersgroep(uuid) ON DELETE CASCADE,
    waardelijst_id VARCHAR(255) NOT NULL,
    PRIMARY KEY (gebruikersgroep_uuid, waardelijst_id)
);

CREATE TABLE IF NOT EXISTS gebruikersgroep_gebruiker (
    gebruikersgroep_uuid UUID NOT NULL REFERENCES gebruikersgroep(uuid) ON DELETE CASCADE,
    gebruiker_id VARCHAR(255) NOT NULL,
    PRIMARY KEY (gebruikersgroep_uuid, gebruiker_id)
);

-- Seed: Local Dev Group
INSERT INTO gebruikersgroep (uuid, naam, omschrijving)
VALUES ('d3da5277-ea07-4921-97b8-e9a181390c76', 'Local Dev Group', 'Default group for local development')
ON CONFLICT (uuid) DO NOTHING;

-- Link dev-user to the group
INSERT INTO gebruikersgroep_gebruiker (gebruikersgroep_uuid, gebruiker_id)
VALUES ('d3da5277-ea07-4921-97b8-e9a181390c76', 'dev-user')
ON CONFLICT DO NOTHING;

-- Add waardelijsten permissions (organisation + information categories)
-- These UUIDs match the publicatiebank fixtures
INSERT INTO gebruikersgroep_waardelijst (gebruikersgroep_uuid, waardelijst_id)
VALUES
    ('d3da5277-ea07-4921-97b8-e9a181390c76', '5e1e724c-c3ea-4d0a-aa79-d0b66aefe27c'),  -- gemeente Appingedam (organisation)
    ('d3da5277-ea07-4921-97b8-e9a181390c76', 'be4e21c2-0be5-4616-945e-1f101b0c0e6d'),  -- Convenant
    ('d3da5277-ea07-4921-97b8-e9a181390c76', '8f3bdef0-a926-4f67-b1f2-94c583c462ce'),  -- Agenda
    ('d3da5277-ea07-4921-97b8-e9a181390c76', '88fb1c5e-e899-456d-b077-6101a9829c11'),  -- Besluitenlijst
    ('d3da5277-ea07-4921-97b8-e9a181390c76', '9aeb7501-3f77-4f36-8c8f-d21f47c2d6e8'),  -- Jaarplan
    ('d3da5277-ea07-4921-97b8-e9a181390c76', 'b84c3b0d-a471-48f5-915f-7fbd8b94188f')   -- Onderzoeksrapport
ON CONFLICT DO NOTHING;
