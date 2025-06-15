# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

Stacksmith is a Docker stack management system for Portainer environments with flexible authentication deployment. The architecture supports decoupled service placement:

- **Management Environment**: Runs Portainer management interface (can be any environment)
- **Auth Environment**: Runs global Authelia instance (typically on publicly accessible environment like VPS)
- **Agent Environments**: Run individual Traefik instances + Portainer agents
- **Flexible Deployment**: Services deployed where they make most operational sense

## Key Components

### Service Templates
- **`traefik/`**: Traefik reverse proxy service with dynamic configuration and environment variables
- **`authelia/`**: Standalone Authelia authentication service with Duo 2FA integration
- **`pihole/`**: Pi-hole DNS and DHCP service with Traefik integration and Authelia authentication

### Key Design Decisions
- **Decoupled Authelia**: Can be deployed independently on publicly accessible environment (e.g., VPS)
- **Flexible Interface Binding**: `TRAEFIK_INTERFACE` allows public or private binding per environment
- **Ultra-Short Hostnames**: 3-4 character subdomains (`mgmt`, `auth`, `prxy`) for concise URLs

### Environment Variable Strategy
- **Management Environment**: `.env.example` (Portainer variables)
- **Traefik Environment**: `traefik/.env.example` (Traefik-specific variables)
- **Auth Environment**: `authelia/.env.example` (Authelia + Traefik variables)
- **Pi-hole Environment**: `pihole/.env.example` (Pi-hole DNS/DHCP + Traefik variables)
- **Agent Environments**: Use `traefik/.env.example` with remote Authelia references

## Common Commands

### Management Environment Deployment
```bash
# Configure management environment
cp .env.example .env
cp traefik/.env.example traefik/.env

# Start Portainer management + Traefik
docker compose -f docker-compose.yml -f traefik/docker-compose.yml up -d
```

### Auth Environment Deployment (e.g., on VPS)
```bash
# Configure authentication environment
cp authelia/.env.example .env

# Start Traefik + Authelia for public authentication
docker compose -f traefik/docker-compose.yml -f authelia/docker-compose.yml up -d
```

### Agent Environment Deployment
```bash
# Configure agent environment
cp traefik/.env.example .env

# Start only Traefik (points to remote Authelia)
docker compose -f traefik/docker-compose.yml up -d
```

### Pi-hole DNS/DHCP Environment Deployment
```bash
# Configure Pi-hole environment
cp pihole/.env.example .env

# Start Pi-hole with Traefik (requires host networking for DHCP)
docker compose -f traefik/docker-compose.yml -f pihole/docker-compose.yml up -d

# Alternative: Pi-hole only (without reverse proxy)
docker compose -f pihole/docker-compose.yml up -d
```

### Service Management
```bash
# View logs for specific services
docker compose logs -f traefik
docker compose logs -f authelia
docker compose logs -f pihole

# Restart services
docker compose restart traefik
docker compose restart authelia
docker compose restart pihole
```

## Critical Configuration Notes

- **Interface Binding**: Use `TRAEFIK_INTERFACE` for flexible public/private binding (defaults to `0.0.0.0`)
- **Authelia Deployment**: Deploy on publicly accessible environment for proper authentication browser redirects
- **Ultra-Short Hostnames**: Concise 3-4 character subdomains (`mgmt.j2.ms`, `auth.j2.ms`, `prxy.j2.ms`, `dns.j2.ms`)
- **Remote Connectivity**: Agent environments connect to Authelia via `AUTHELIA_HOST` and `AUTHELIA_HOSTNAME`
- **Let's Encrypt**: Uses Cloudflare DNS-01 challenge (requires API token)
- **Default Credentials**: Authelia admin/password (change hash in `users_database.yml`)
- **Pi-hole DHCP**: Uses host networking mode for DHCP functionality; disable existing DHCP server on router
- **Pi-hole DNS**: Runs on port 53 (DNS) and custom web port (default 8080) for Traefik integration
- **DHCP Relay**: UCG Fiber should be configured as DHCP relay pointing to Pi-hole container IP

## Common Deployment Scenarios

**Home + VPS Setup:**
- VPS: `traefik/docker-compose.yml + authelia/docker-compose.yml` (public authentication)
- Home: `docker-compose.yml + traefik/docker-compose.yml` (private management)
- Agent environments point to VPS Authelia for authentication