# syntax=docker/dockerfile:1
# Frontend + Caddy - builds Vue.js and serves via Caddy

FROM oven/bun:1-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json bun.lockb* ./

# Install dependencies
RUN bun install --frozen-lockfile || bun install

# Copy source
COPY . .

# Build for production
RUN bun run build-only

# Production stage - Caddy serves the static files
FROM caddy:2-alpine AS production

# Copy built assets
COPY --from=builder /app/dist /srv

# Caddyfile for SPA serving with API proxy
COPY <<EOF /etc/caddy/Caddyfile
:80 {
    # API v2 routes go to gpp-api (data backend)
    handle /api/v2/* {
        reverse_proxy gpp-api:8000
    }

    # API v1 and auth routes go to gpp-app-fastapi (BFF)
    handle /api/* {
        reverse_proxy gpp-app-fastapi:8000
    }

    # Serve static files
    handle {
        root * /srv
        try_files {path} /index.html
        file_server
    }

    # Cache hashed assets
    @hashed path_regexp hash .*-[a-zA-Z0-9]{8}\.(js|css)$
    header @hashed Cache-Control "public, max-age=8640000, immutable"

    # No cache for index.html
    @html path *.html /
    header @html Cache-Control "no-cache"
}
EOF

EXPOSE 80

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]
