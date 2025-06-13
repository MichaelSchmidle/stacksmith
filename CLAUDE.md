# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

Stacksmith is a Docker stack management system for Portainer environments with centralized SSO. The architecture follows a hub-and-spoke model:

- **Main Environment**: Runs Portainer management interface + global Authelia SSO instance
- **Remote Environments**: Run individual Traefik instances + Portainer agents that connect back to main
- **Single Global Authelia**: Provides SSO across all environments via Tailscale network connectivity

## Key Components

### Shared Traefik Template (`shared/docker-compose.traefik.yml`)
Reusable Traefik service definition that can be deployed to any environment. Uses variable substitution for:
- Container naming (`TRAEFIK_CONTAINER_NAME`)
- Remote Authelia connectivity (`AUTHELIA_HOST`, `AUTHELIA_DOMAIN`)
- Environment-specific domains (`DOMAIN_NAME`)

### Authelia Configuration (`shared/authelia/`)
Global SSO configuration with Duo 2FA integration. Only runs on main environment but serves all others via forwardauth middleware pointing to Tailscale IPs.

### Environment Variable Strategy
- Main environment: Full variable set including Authelia secrets
- Remote environments: Minimal set + `AUTHELIA_HOST` pointing to main environment's Tailscale IP

## Common Commands

### Main Environment Deployment
```bash
# Copy and configure environment variables
cp .env.example .env

# Start Portainer + Authelia + Traefik
docker compose -f docker-compose.yml -f shared/docker-compose.traefik.yml up -d
```

### Remote Environment Deployment
```bash
# Start only Traefik (points to remote Authelia)
docker compose -f shared/docker-compose.traefik.yml up -d
```

### Service Management
```bash
# View logs for specific services
docker compose logs -f traefik
docker compose logs -f authelia

# Restart services
docker compose restart traefik
docker compose restart authelia
```

## Critical Configuration Notes

- All services bind only to Tailscale interface (`TAILSCALE_INTERFACE` env var)
- Authelia middleware configured via `authelia@docker` label in Traefik
- Remote environments must have network connectivity to main environment's Authelia on port 9091
- Let's Encrypt certificates use Cloudflare DNS-01 challenge (requires API token)
- Default Authelia user is admin/password (change hash in `users_database.yml`)