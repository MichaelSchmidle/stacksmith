# Stacksmith

Docker stack management for Portainer environments with Traefik reverse proxy and Authelia SSO.

## Architecture

- **Main Environment**: Runs Portainer management interface + global Authelia SSO
- **Other Environments**: Run Portainer agents + individual Traefik instances
- **Single Global Authelia**: Provides SSO across all environments via Tailscale network

## Quick Start

### Main Environment (Management + SSO)

1. Copy environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. Start main services:
   ```bash
   docker compose -f docker-compose.yml -f shared/docker-compose.traefik.yml up -d
   ```

### Other Environments (Agents Only)

1. Create `.env` file with:
   ```bash
   # Required for Traefik
   DOMAIN_NAME=your-env.example.com
   TAILSCALE_INTERFACE=100.64.0.1
   ACME_EMAIL=your-email@example.com
   CLOUDFLARE_API_TOKEN=your-token
   
   # Point to main environment's Authelia
   AUTHELIA_HOST=100.64.0.1  # Main environment's Tailscale IP
   AUTHELIA_DOMAIN=main.example.com
   ```

2. Start Traefik only:
   ```bash
   docker compose -f shared/docker-compose.traefik.yml up -d
   ```

3. Deploy Portainer agent via Portainer UI or CLI commands

## Environment Variables

See `.env.example` for all required variables including:
- Domain and Tailscale configuration
- Authelia JWT/session secrets
- Cloudflare API token for Let's Encrypt
- SMTP settings for Authelia notifications
- Duo 2FA integration keys

## Services

- **Portainer**: `https://your-domain.com` (management interface)
- **Authelia**: `https://auth.your-domain.com` (SSO login)
- **Traefik**: `https://traefik.your-domain.com` (dashboard)

## Security

- All services bind only to Tailscale interface
- Authelia provides Duo 2FA protection
- Let's Encrypt certificates via Cloudflare DNS-01 challenge

