# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

Stacksmith is a Docker stack management system for Portainer environments with flexible SSO deployment. The architecture supports decoupled service placement:

- **Management Environment**: Runs Portainer management interface (can be any environment)
- **SSO Environment**: Runs global Authelia instance (typically on publicly accessible environment like VPS)
- **Agent Environments**: Run individual Traefik instances + Portainer agents
- **Flexible Deployment**: Services deployed where they make most operational sense

## Key Components

### Shared Service Templates
- **`shared/docker-compose.traefik.yml`**: Reusable Traefik service for any environment
- **`shared/docker-compose.authelia.yml`**: Standalone Authelia service for flexible deployment
- **`shared/authelia/`**: Global SSO configuration with Duo 2FA integration

### Key Design Decisions
- **Decoupled Authelia**: Can be deployed independently on publicly accessible environment (e.g., VPS)
- **Flexible Interface Binding**: `TRAEFIK_INTERFACE` allows public or private binding per environment
- **Ultra-Short Hostnames**: 3-4 character subdomains (`mgmt`, `auth`, `prxy`) for concise URLs

### Environment Variable Strategy
- **Management Environment**: `.env.example` (Portainer + Traefik variables)
- **SSO Environment**: `shared/.env.authelia.example` (Authelia + Traefik variables)
- **Agent Environments**: Minimal Traefik variables + remote Authelia references

## Common Commands

### Management Environment Deployment
```bash
# Copy and configure environment variables
cp .env.example .env

# Start Portainer management + Traefik
docker compose -f docker-compose.yml -f shared/docker-compose.traefik.yml up -d
```

### SSO Environment Deployment (e.g., on VPS)
```bash
# Copy Authelia environment variables
cp shared/.env.authelia.example .env

# Start Traefik + Authelia for public SSO
docker compose -f shared/docker-compose.traefik.yml -f shared/docker-compose.authelia.yml up -d
```

### Agent Environment Deployment
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

- **Interface Binding**: Use `TRAEFIK_INTERFACE` for flexible public/private binding (defaults to `0.0.0.0`)
- **Authelia Deployment**: Deploy on publicly accessible environment for proper SSO browser redirects
- **Ultra-Short Hostnames**: Concise 3-4 character subdomains (`mgmt.j2.ms`, `auth.j2.ms`, `prxy.j2.ms`)
- **Remote Connectivity**: Agent environments connect to Authelia via `AUTHELIA_HOST` and `AUTHELIA_HOSTNAME`
- **Let's Encrypt**: Uses Cloudflare DNS-01 challenge (requires API token)
- **Default Credentials**: Authelia admin/password (change hash in `users_database.yml`)

## Common Deployment Scenarios

**Home + VPS Setup:**
- VPS: `docker-compose.traefik.yml + docker-compose.authelia.yml` (public SSO)
- Home: `docker-compose.yml + docker-compose.traefik.yml` (private management)
- Agent environments point to VPS Authelia for SSO