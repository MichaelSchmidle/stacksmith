# OAuth2-Proxy Stack

Centralized authentication service for protecting services across multiple Docker hosts.

## Setup

1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

2. Generate cookie secret:
   ```bash
   openssl rand -base64 32
   ```

3. Deploy the stack:
   ```bash
   docker compose up -d
   ```

## Configuration

- Deploy only on one host (authentication server)
- Other Traefik instances will forward auth requests to this service
- All services using `oauth2-proxy` middleware will be protected

## Network Requirements

- OAuth2-Proxy must be accessible from all Traefik instances
- Uses `stacksmith` external network for service discovery