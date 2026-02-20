# GPP App (FastAPI)

FastAPI BFF (Backend for Frontend) for GPP - replaces the C#/.NET ODPC.Server.

## Overview

GPP App handles OIDC authentication and proxies requests to the gpp-api backend.
It also manages user groups (Gebruikersgroepen) for access control.

## Features

- **OIDC Authentication**: OpenID Connect integration with dev auto-login mode
- **User Groups**: Manage user groups and their access to value lists
- **Proxy to gpp-api**: Forward publication/document requests with audit headers
- **woo-hoo Integration**: Metadata generation via LLM service

## Quick Start

```bash
# Install dependencies
just install-dev

# Run development server
just dev

# Run tests
just test
```

## Project Structure

```
src/gpp_app/
├── main.py              # FastAPI application factory
├── config.py            # Pydantic settings
├── auth/
│   ├── oidc.py          # OIDC authentication
│   └── permissions.py   # Authorization helpers
├── db/
│   ├── engine.py        # SQLAlchemy async engine
│   └── models/          # User group models
├── api/
│   ├── auth.py          # /api/me, /api/challenge, etc.
│   ├── user_groups.py   # User group CRUD
│   ├── publications.py  # Publication proxy
│   ├── documents.py     # Document proxy
│   └── metadata.py      # Metadata endpoints
├── services/
│   └── gpp_api_client.py  # gpp-api HTTP client
└── utils/
    └── logging.py       # Structured logging
```

## API Endpoints

### Authentication
- `GET /api/me` - Current user info
- `GET /api/challenge` - OIDC login
- `GET /api/callback` - OIDC callback
- `GET /api/logoff` - Logout

### User Groups (Admin only)
- `GET /api/v1/gebruikersgroepen` - List groups
- `GET /api/v1/gebruikersgroepen/{uuid}` - Get group
- `POST /api/v1/gebruikersgroepen` - Create group
- `PUT /api/v1/gebruikersgroepen/{uuid}` - Update group
- `DELETE /api/v1/gebruikersgroepen/{uuid}` - Delete group

### User's Groups
- `GET /api/v1/mijn-gebruikersgroepen` - User's groups and value lists

### Publications (Proxy to gpp-api)
- `GET /api/v1/publicaties` - List
- `GET /api/v1/publicaties/{uuid}` - Get
- `POST /api/v1/publicaties` - Create
- `PUT /api/v1/publicaties/{uuid}` - Update
- `DELETE /api/v1/publicaties/{uuid}` - Delete
- `POST /api/v1/publicaties/{uuid}/publish` - Publish
- `POST /api/v1/publicaties/{uuid}/revoke` - Revoke

### Documents (Proxy to gpp-api)
- `GET /api/v1/documenten` - List
- `GET /api/v1/documenten/{uuid}` - Get
- `POST /api/v1/documenten` - Create
- `PUT /api/v1/documenten/{uuid}` - Update
- `DELETE /api/v1/documenten/{uuid}` - Delete

### Metadata
- `GET /api/v1/metadata/health` - woo-hoo health check
- `POST /api/v1/metadata/generate/{uuid}` - Generate metadata
- `GET /api/v1/organisaties` - List organisations
- `GET /api/v1/informatiecategorieen` - List categories
- `GET /api/v1/onderwerpen` - List topics

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql+asyncpg://...` |
| `GPP_API_BASE_URL` | gpp-api backend URL | `http://gpp-api:8000` |
| `GPP_API_TOKEN` | API token for gpp-api | - |
| `WOO_HOO_BASE_URL` | woo-hoo service URL | `http://woo-hoo:8000` |
| `OIDC_AUTHORITY` | OIDC authority URL | (empty = dev mode) |
| `OIDC_CLIENT_ID` | OIDC client ID | - |
| `OIDC_CLIENT_SECRET` | OIDC client secret | - |
| `OIDC_ADMIN_ROLE` | Admin role claim value | `odpc-admin` |
| `SESSION_SECRET_KEY` | Session encryption key | - |
| `LOG_LEVEL` | Log level | `INFO` |

## Dev Mode

When `OIDC_AUTHORITY` is not set, the service runs in development mode:
- All requests are automatically authenticated as admin
- No OIDC redirect is performed

## License

EUPL-1.2
