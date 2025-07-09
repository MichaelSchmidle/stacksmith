# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Stacksmith - Docker Infrastructure Management System

## Repository Overview

Stacksmith is a modular Docker-based infrastructure management system built around **Portainer** as the central management interface. It provides a complete self-hosted solution for managing containerized applications with enterprise-grade security, SSL automation, and flexible service composition.

## Architecture

### Core Philosophy
- **Modular Design**: Each service is independently deployable and composable
- **Security-First**: Integrated with Tailscale VPN and enterprise OAuth
- **Flexible Deployment**: Services can be deployed where operationally optimal
- **Self-Hosted Focus**: Complete infrastructure stack without external dependencies

### Core Infrastructure
- **Portainer** (`/docker-compose.yml`) - Docker management web interface
- **Traefik** (`/traefik/`) - Reverse proxy with automatic HTTPS

Additional services are available in their respective directories, each with comprehensive documentation in their individual README.md files.

## Common Patterns

### Docker Compose Structure
All services follow a consistent pattern:

```yaml
# NOTE: The 'version' field has been deprecated and should not be used
services:
  service-name:
    image: service/image:latest
    container_name: stacksmith_servicename
    restart: unless-stopped
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - TZ=${TZ}
    volumes:
      - service-data:/data
    networks:
      - stacksmith
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.service.rule=Host(`${SERVICE_HOSTNAME}`)"
      - "traefik.http.routers.service.entrypoints=websecure-tailscale"
      - "traefik.http.routers.service.tls.certresolver=stacksmith"
      - "traefik.http.services.service.loadbalancer.server.port=PORT"
      - "traefik.http.routers.service.middlewares=secure-headers@docker"
```

### Key Patterns
- **Consistent naming**: All containers prefixed with `stacksmith_`
- **External network**: All services join the `stacksmith` network
- **Traefik integration**: Automatic service discovery via Docker labels
- **Volume management**: Named volumes for persistence, bind mounts for config
- **User management**: Consistent PUID/PGID across LinuxServer images
- **Hostname convention**: Ultra-short 3-4 character hostnames that abstract the function (e.g., `dns` for Pi-hole, `mgmt` for Portainer)
- **Subdomain routing**: Prefer subdomains over complex path routing for services with multiple endpoints (e.g., `api.service.example.com` instead of `service.example.com/api`)

## Network Architecture

### Tailscale Integration
- **Primary Access**: Services bound to Tailscale IP (100.64.0.1)
- **Secure Overlay**: All services accessible via Tailscale VPN
- **Dual Entrypoints**: Primary (Tailscale) and secondary interfaces

### Traefik Configuration
```yaml
# Entrypoint Configuration (internal container ports)
- --entrypoints.web-tailscale.address=:80
- --entrypoints.websecure-tailscale.address=:443
- --entrypoints.web-secondary.address=:8080
- --entrypoints.websecure-secondary.address=:8443

# Port Mappings (external_ip:external_port:internal_port)
ports:
  - "${TRAEFIK_TAILSCALE_IP}:80:80"
  - "${TRAEFIK_TAILSCALE_IP}:443:443"
  - "${TRAEFIK_SECONDARY_IP}:80:8080"
  - "${TRAEFIK_SECONDARY_IP}:443:8443"
```

### SSL/TLS Management
- **Let's Encrypt**: Automatic certificate generation
- **Cloudflare DNS Challenge**: Wildcard certificate support
- **Strong TLS**: Custom configuration in `/traefik/dynamic/tls.yml`

## Environment Configuration

### Multi-layered System
- **Main Environment** (`/.env.example`): Core infrastructure settings
- **Service-specific** (`/service/.env.example`): Individual service configuration

### Key Environment Variables
```bash
# Core Infrastructure
PORTAINER_HOSTNAME=mgmt.example.com
TRAEFIK_HOSTNAME=prxy.example.com
TRAEFIK_TAILSCALE_IP=100.64.0.1
TRAEFIK_SECONDARY_IP=127.0.0.1

# SSL Configuration
ACME_EMAIL=your-email@example.com
CLOUDFLARE_DNS_API_TOKEN=your-cloudflare-api-token

# Timezone Configuration
# IMPORTANT: Always use Europe/Zurich as the default timezone in .env.example files
TZ=Europe/Zurich
```

## Deployment Patterns

### Network Setup
```bash
# Create external network (required first step)
docker network create stacksmith
```

### Core Management Stack
```bash
docker compose -f docker-compose.yml -f traefik/docker-compose.yml up -d
```

### Adding Services
```bash
# Deploy any additional service
docker compose -f traefik/docker-compose.yml -f servicename/docker-compose.yml up -d

# Deploy multiple services together
docker compose -f docker-compose.yml -f traefik/docker-compose.yml -f service1/docker-compose.yml -f service2/docker-compose.yml up -d
```

## Security Model

### Authentication Architecture
- **JumpCloud OAuth**: Optional for Portainer only (configuration in `/PORTAINER_OAUTH_SETUP.md`)
- **Tailscale VPN**: Primary access method for all services
- **Service-level Authentication**: Individual service security

### Network Security
- **Tailscale VPN**: Primary access method
- **Network Isolation**: Services communicate through dedicated network
- **HTTPS Enforcement**: Automatic HTTP to HTTPS redirect

### Configuration Security
- **No Default Passwords**: Secure defaults across all services
- **API Token Management**: Scoped tokens for external services
- **Certificate Automation**: Automated SSL certificate management

## Core Infrastructure Details

### Portainer Configuration
- **Docker Socket Access**: Full Docker management capabilities
- **OAuth Integration**: Post-deployment JumpCloud configuration
- **Volume Persistence**: Configuration stored in named volume

### Traefik Features
- **Dynamic Configuration**: File provider for custom configurations
- **Service Discovery**: Automatic Docker service detection
- **Load Balancing**: Built-in load balancing capabilities
- **Middleware Support**: Authentication, rate limiting, headers

## Common Commands

### Prerequisites
```bash
# Always create the external network first (only needed once)
docker network create stacksmith
```

### Service Management
```bash
# Deploy specific service
docker compose -f servicename/docker-compose.yml up -d

# Deploy multiple services together
docker compose -f docker-compose.yml -f traefik/docker-compose.yml up -d

# View service logs
docker compose logs -f servicename

# Update service
docker compose pull servicename
docker compose up -d servicename

# Stop services
docker compose down

# Remove services and volumes (destructive)
docker compose down -v
```

### Environment Setup
```bash
# Copy environment files for new services
cp .env.example .env
cp servicename/.env.example servicename/.env

# Edit environment files with service-specific values
# Required: Set hostnames, IPs, and tokens
```

### Backup Operations
```bash
# Backup named volume
docker run --rm -v volumename:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz /data

# Restore named volume
docker run --rm -v volumename:/data -v $(pwd):/backup alpine tar xzf /backup/backup.tar.gz -C /
```

## Development and Contribution Guidelines

### Repository Structure
- **Flat Organization**: Each service in its own directory
- **Independent Services**: Services can be developed and deployed independently
- **Consistent Patterns**: Follow established patterns for new services

### Adding New Services
1. Create service directory: `mkdir servicename`
2. Create `docker-compose.yml` following the standard pattern
3. **ALWAYS create `.env.example`** with service-specific variables
4. **ALWAYS create `README.md`** with comprehensive documentation
5. Follow Traefik integration patterns:
   - Use `websecure-tailscale` entrypoint (or `websecure-secondary` if needed)
   - Include required Traefik labels
   - Set correct service port
6. Use consistent naming: `stacksmith_servicename`
7. Join `stacksmith` external network
8. Include standard environment variables (PUID, PGID, TZ) when applicable

### Documentation Requirements
- **CRITICAL**: Every service MUST have both `.env.example` and `README.md` files
- **Keep Documentation Updated**: When modifying services, update both files accordingly
- **Environment Variables**: Document all variables in both `.env.example` and `README.md`
- **Deployment Instructions**: Include complete deployment steps in README
- **Troubleshooting**: Add common issues and solutions to README

### Environment Management
- **No Production Secrets**: Use `.env.example` templates only
- **Clear Documentation**: Document all environment variables
- **Secure Defaults**: Provide secure default configurations
- **Consistency**: Follow the same .env.example format across all services

## Key Advantages

### Operational Benefits
- **Single Management Interface**: Portainer provides unified container management
- **Flexible Deployment**: Services can be deployed across multiple environments
- **Enterprise Security**: Integrated VPN and OAuth authentication
- **Automated SSL**: Let's Encrypt with DNS challenge automation

### Technical Benefits
- **Modular Architecture**: Add/remove services without affecting others
- **Standard Images**: Uses official and well-maintained container images
- **No Custom Builds**: Pure Docker Compose without complex build processes
- **Scalable Design**: Supports multi-environment and multi-host deployments

### Security Benefits
- **VPN-First Access**: Tailscale integration for secure remote access
- **Automated Certificates**: Let's Encrypt with Cloudflare DNS challenges
- **Network Isolation**: Services communicate through dedicated networks
- **Enterprise Authentication**: JumpCloud OAuth integration

This repository represents a mature, production-ready Docker infrastructure system suitable for personal use, home labs, or small to medium business deployments.

## Local Development and Testing

### Local Testing Workflow
For testing changes before committing, replicate the production environment locally:

1. **Setup**: Ensure `*.dev.example.com` resolves to `127.0.0.1` via Cloudflare DNS
2. **Environment**: Set `TRAEFIK_TAILSCALE_IP=127.0.0.1` in local `.env` files
3. **Deploy**: Use standard Docker Compose commands with local domains
4. **Test**: Verify service accessibility and SSL certificate generation

### When Testing Changes
- Prompt user for their actual test domain (don't read .env files)
- Use the domain from user's `~/.claude/CLAUDE.md` memory if available
- Test complete deployment workflow including Traefik routing

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER ever read `.env` files as contained secrets would leak into your logs/telemetry at Anthropic.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
