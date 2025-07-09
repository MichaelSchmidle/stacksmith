# Stacksmith - Docker Infrastructure Management System

Stacksmith is a modular Docker-based infrastructure management system built around **Portainer** as the central management interface. It provides a complete self-hosted solution for managing containerized applications with enterprise-grade security, SSL automation, and flexible service composition.

## Core Services

- **Portainer** (`docker-compose.yml`) - Docker management web interface
- **Traefik** (`traefik/`) - Reverse proxy with automatic HTTPS

## Quick Start

### Prerequisites

```bash
# Create the external network (required for all services)
docker network create stacksmith
```

### Basic Setup (Portainer + Traefik)

1. **Configure Environment**:
```bash
cp .env.example .env
cp traefik/.env.example traefik/.env
# Edit both .env files with your hostnames and settings
```

2. **Deploy Core Infrastructure**:
```bash
docker compose -f docker-compose.yml -f traefik/docker-compose.yml up -d
```

3. **Access Portainer**: Navigate to your configured hostname (e.g., `https://mgmt.example.com`)

## Architecture

### Core Philosophy
- **Modular Design**: Each service is independently deployable and composable
- **Security-First**: Integrated with Tailscale VPN and enterprise OAuth
- **Flexible Deployment**: Services can be deployed where operationally optimal
- **Self-Hosted Focus**: Complete infrastructure stack without external dependencies

### Service Composition

Deploy additional services by combining Docker Compose files:

```bash
# Add any service to the core infrastructure
docker compose -f docker-compose.yml -f traefik/docker-compose.yml -f servicename/docker-compose.yml up -d

# Deploy multiple services together
docker compose -f traefik/docker-compose.yml -f service1/docker-compose.yml -f service2/docker-compose.yml up -d
```

## Configuration

### Environment Structure
- **Main Environment** (`/.env.example`): Core infrastructure settings
- **Service-specific** (`/service/.env.example`): Individual service configuration

### Core Environment Variables
```bash
# Core Infrastructure
PORTAINER_HOSTNAME=mgmt.example.com
TRAEFIK_HOSTNAME=prxy.example.com
TRAEFIK_TAILSCALE_IP=100.64.0.1
TRAEFIK_SECONDARY_IP=127.0.0.1

# SSL Configuration
ACME_EMAIL=your-email@example.com
CLOUDFLARE_DNS_API_TOKEN=your-cloudflare-api-token
```

## Available Services

Each service is in its own directory with complete documentation:

- **Pi-hole** (`pihole/`) - DNS server with ad-blocking
- **Media Stack** (`arr/`) - Complete media automation suite
- **n8n** (`n8n/`) - Workflow automation platform
- **Matomo** (`matomo/`) - Privacy-focused web analytics
- **Uptime Kuma** (`uptimekuma/`) - Uptime monitoring
- **Home Assistant** (`homeassistant/`) - Home automation platform

Each service includes:
- `docker-compose.yml` - Service configuration
- `.env.example` - Environment template
- `README.md` - Complete service documentation

## Network Architecture

### Tailscale Integration
- **Primary Access**: Services bound to Tailscale IP (100.64.0.1)
- **Secure Overlay**: All services accessible via Tailscale VPN
- **Dual Entrypoints**: Primary (Tailscale) and secondary interfaces

### SSL/TLS Management
- **Let's Encrypt**: Automatic certificate generation
- **Cloudflare DNS Challenge**: Wildcard certificate support
- **Strong TLS**: Custom security configuration

## Authentication

### Tailscale VPN Access
Primary access method for all services via Tailscale VPN. Optional JumpCloud OAuth for Portainer only (see `PORTAINER_OAUTH_SETUP.md`).

## Service Management

### Common Commands
```bash
# Deploy specific service
docker compose -f servicename/docker-compose.yml up -d

# View service logs
docker compose logs -f servicename

# Update service
docker compose pull servicename
docker compose up -d servicename

# Stop services
docker compose down
```

### Backup Operations
```bash
# Backup named volume
docker run --rm -v volumename:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz /data

# Restore named volume
docker run --rm -v volumename:/data -v $(pwd):/backup alpine tar xzf /backup/backup.tar.gz -C /
```

## Deployment Patterns

### Home Lab Setup
```bash
docker network create stacksmith
docker compose -f docker-compose.yml -f traefik/docker-compose.yml up -d
```

### Multi-Service Deployment
```bash
# Add multiple services to core infrastructure
docker compose -f docker-compose.yml -f traefik/docker-compose.yml -f pihole/docker-compose.yml -f uptimekuma/docker-compose.yml up -d
```

### Remote Agent Setup
Deploy Portainer agents on remote Docker hosts for centralized management:
```bash
docker run -d \
  -p 9001:9001 \
  --name portainer_agent \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  portainer/agent:latest
```

## Security

- **VPN-First Access**: Tailscale integration for secure remote access
- **Automated Certificates**: Let's Encrypt with Cloudflare DNS challenges
- **Network Isolation**: Services communicate through dedicated networks
- **Enterprise Authentication**: JumpCloud OAuth integration
- **No Default Passwords**: Secure defaults across all services

## Troubleshooting

### Network Issues
```bash
# Verify external network exists
docker network ls | grep stacksmith

# Recreate network if needed
docker network rm stacksmith
docker network create stacksmith
```

### Service Access Issues
```bash
# Check Traefik routing
docker compose logs traefik | grep servicename

# Verify DNS resolution
nslookup your-hostname.example.com

# Test container connectivity
docker compose exec servicename ping traefik
```

## Local Development and Testing

Test changes locally before committing to avoid production deployment issues.

### Prerequisites
- Docker and Docker Compose
- Wildcard DNS: `*.dev.example.com` → `127.0.0.1`
- Cloudflare DNS API token

### Setup
```bash
# Create network and copy environment files
docker network create stacksmith
cp .env.example .env
cp servicename/.env.example servicename/.env

# Update .env files:
# - Set TRAEFIK_TAILSCALE_IP=127.0.0.1
# - Use local domains (e.g., mgmt.dev.example.com)

# Deploy and test
docker compose -f docker-compose.yml -f traefik/docker-compose.yml up -d
docker compose -f traefik/docker-compose.yml -f servicename/docker-compose.yml up -d
curl -k https://mgmt.dev.example.com
```

### For Claude Code Users
Use the `#` memory shortcut to store your test domain:
```
# Stacksmith local testing: Use *.dev.example.com for local development domains in this repo
```

## Contributing

When adding new services:
1. Create service directory with consistent naming
2. Include `docker-compose.yml`, `.env.example`, and `README.md`
3. Follow established patterns for Traefik integration
4. Use `stacksmith_` container naming convention
5. Join the `stacksmith` external network
6. Document all configuration in service README
7. **Test locally** before committing changes

This repository represents a mature, production-ready Docker infrastructure system suitable for personal use, home labs, or small to medium business deployments.