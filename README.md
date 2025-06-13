# Stacksmith

Docker stack management for Portainer environments with Traefik reverse proxy and Authelia authentication.

## Architecture

- **Management Environment**: Runs Portainer management interface (can be any environment)
- **Auth Environment**: Runs global Authelia instance (typically on publicly accessible environment)
- **Agent Environments**: Run Portainer agents + individual Traefik instances
- **Flexible Deployment**: Deploy services where they make most sense (Authelia on VPS, management on home network)

## Quick Start

### Management Environment

1. Copy environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. Start Portainer management:
   ```bash
   docker compose -f docker-compose.yml -f shared/docker-compose.traefik.yml up -d
   ```

### Auth Environment (Authelia)

Deploy on publicly accessible environment (e.g., VPS):
```bash
# Copy Authelia environment variables
cp shared/.env.authelia.example .env

# Start Traefik + Authelia for public authentication
docker compose -f shared/docker-compose.traefik.yml -f shared/docker-compose.authelia.yml up -d
```

### Agent Environments

Deploy via Portainer management interface using `shared/docker-compose.traefik.yml` as the stack definition.

## Environment Variables

**Management Environment**: See `.env.example`  
**Auth Environment**: See `shared/.env.authelia.example`

Variables include:
- Ultra-short hostnames (`mgmt`, `auth`, `prxy`)
- Network interface binding (`TRAEFIK_INTERFACE`)
- Authelia JWT/session secrets (auth environment only)
- Cloudflare API token for Let's Encrypt
- SMTP settings and Duo 2FA integration

## Services

Services are accessible via fully customizable hostnames:
- **Portainer**: Management interface (e.g., `mgmt.j2.ms`)
- **Authelia**: Authentication service (e.g., `auth.j2.ms`)  
- **Traefik**: Dashboard (e.g., `prxy.j2.ms`)

## Security

- Management interface can bind to Tailscale for enhanced security
- Authelia deployed on publicly accessible environment for proper authentication redirects
- All environments support flexible interface binding (private/public)
- Duo 2FA protection across all services and environments
- Let's Encrypt certificates via Cloudflare DNS-01 challenge

## Deployment Examples

**Scenario 1: Home + VPS**
- VPS: Traefik + Authelia (public authentication)
- Home: Traefik + Portainer management (private)
- All services authenticate via VPS Authelia

**Scenario 2: All Public**  
- Single VPS: All services with global authentication

