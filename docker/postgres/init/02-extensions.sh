#!/bin/bash
set -e

# Install PostGIS and other extensions in openzaak database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "openzaak" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
EOSQL

# Install PostGIS in woo_publications database (if needed)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "woo_publications" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS postgis;
EOSQL
