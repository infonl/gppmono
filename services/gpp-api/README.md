# GPP API

FastAPI backend for GPP (Generiek Publicatieplatform) - replaces the Django publicatiebank service.

## Overview

GPP API manages publications, documents, and metadata for Dutch government Woo (Wet open overheid) compliance.

## Features

- **Publications Management**: CRUD operations for publications with state machine (concept → gepubliceerd → ingetrokken)
- **Documents Management**: File upload/download with OpenZaak Documents API integration
- **Metadata**: Organisations, Information Categories, Topics, Themes
- **Background Workers**: Redis Streams for async indexing to gpp-zoeken
- **Admin Interface**: Starlette-Admin for data management

## Quick Start

```bash
# Install dependencies
just install-dev

# Run development server
just dev

# Run tests
just test

# Run worker
just worker
```

## Project Structure

```
src/gpp_api/
├── main.py              # FastAPI application factory
├── config.py            # Pydantic settings
├── db/
│   ├── engine.py        # SQLAlchemy async engine
│   └── models/          # Database models
├── api/
│   ├── deps.py          # FastAPI dependencies
│   └── routers/         # API endpoints
├── schemas/             # Pydantic request/response models
├── services/            # Business logic services
├── workers/             # Redis Streams background workers
├── admin/               # Starlette-Admin views
└── utils/               # Logging, audit utilities
```

## API Endpoints

### Publications (`/api/v2/publicaties`)
- `GET /api/v2/publicaties` - List publications
- `GET /api/v2/publicaties/{uuid}` - Get publication
- `POST /api/v2/publicaties` - Create publication
- `PUT /api/v2/publicaties/{uuid}` - Update publication
- `DELETE /api/v2/publicaties/{uuid}` - Delete publication
- `POST /api/v2/publicaties/{uuid}/publish` - Publish
- `POST /api/v2/publicaties/{uuid}/revoke` - Revoke

### Documents (`/api/v2/documenten`)
- `GET /api/v2/documenten` - List documents
- `GET /api/v2/documenten/{uuid}` - Get document
- `POST /api/v2/documenten` - Create document
- `PUT /api/v2/documenten/{uuid}` - Update document
- `DELETE /api/v2/documenten/{uuid}` - Delete document
- `POST /api/v2/documenten/{uuid}/upload` - Upload file
- `GET /api/v2/documenten/{uuid}/download` - Download file

### Metadata
- `GET /api/v2/organisaties` - List organisations
- `GET /api/v2/informatiecategorieen` - List information categories
- `GET /api/v2/onderwerpen` - List topics

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/3` |
| `OPENZAAK_DOCUMENTS_API_URL` | OpenZaak Documents API | - |
| `OPENZAAK_CATALOGI_API_URL` | OpenZaak Catalogi API | - |
| `OPENZAAK_CLIENT_ID` | OpenZaak client ID | - |
| `OPENZAAK_SECRET` | OpenZaak secret | - |
| `GPP_ZOEKEN_URL` | Search service URL | - |
| `LOG_LEVEL` | Log level | `INFO` |
| `LOG_FORMAT` | Log format (json/console) | `json` |

## Development

```bash
# Format code
just fmt

# Lint
just lint

# Type check
just typecheck

# All checks
just check

# Generate migration
just migration "description"

# Run migrations
just migrate
```

## Docker

```bash
# Build image
just docker-build

# Run container
just docker-run
```

## License

EUPL-1.2
