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

### Service Categories

#### Core Infrastructure
- **Portainer** (`/docker-compose.yml`) - Docker management web interface
- **Traefik** (`/traefik/`) - Reverse proxy with automatic HTTPS

#### Network Services
- **Pi-hole** (`/pihole/`) - DNS server with ad-blocking capabilities

#### Media Management
- ***arr Stack** (`/arr/`) - Complete media automation suite:
  - Sonarr (TV series management)
  - Radarr (movie management)
  - Prowlarr (indexer management)
  - qBittorrent (download client)
  - Recyclarr (quality profile management)
  - qbit_manage (automated cleanup)

#### Productivity Tools
- **n8n** (`/n8n/`) - Workflow automation platform

## Common Patterns

### Docker Compose Structure
All services follow a consistent pattern:

```yaml
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
```

### Key Patterns
- **Consistent naming**: All containers prefixed with `stacksmith_`
- **External network**: All services join the `stacksmith` network
- **Traefik integration**: Automatic service discovery via Docker labels
- **Volume management**: Named volumes for persistence, bind mounts for config
- **User management**: Consistent PUID/PGID across LinuxServer images
- **Hostname convention**: Ultra-short 3-4 character hostnames that abstract the function (e.g., `dns` for Pi-hole, `mgmt` for Portainer)

## Network Architecture

### Tailscale Integration
- **Primary Access**: Services bound to Tailscale IP (100.64.0.1)
- **Secure Overlay**: All services accessible via Tailscale VPN
- **Dual Entrypoints**: Primary (Tailscale) and secondary interfaces

### Traefik Configuration
```yaml
# Entrypoint Configuration
- --entrypoints.web-tailscale.address=:80
- --entrypoints.websecure-tailscale.address=:443
- --entrypoints.web-secondary.address=:8080
- --entrypoints.websecure-secondary.address=:8443
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

# Service Hostnames
PIHOLE_WEB_HOSTNAME=dns.example.com
SONARR_HOSTNAME=tvs.example.com
RADARR_HOSTNAME=movies.example.com
```

## Deployment Patterns

### Network Setup
```bash
# Create external network (required first step)
docker network create stacksmith
```

### Service Composition Examples

#### Core Management Stack
```bash
docker compose -f docker-compose.yml -f traefik/docker-compose.yml up -d
```

#### Add DNS Service
```bash
docker compose -f docker-compose.yml -f traefik/docker-compose.yml -f pihole/docker-compose.yml up -d
```

#### Media Management Stack
```bash
docker compose -f traefik/docker-compose.yml -f arr/docker-compose.yml up -d
```

#### Full Infrastructure
```bash
docker compose -f docker-compose.yml -f traefik/docker-compose.yml -f pihole/docker-compose.yml -f arr/docker-compose.yml up -d
```

## Security Model

### Authentication Architecture
- **JumpCloud OAuth**: Enterprise identity management (configuration in `/PORTAINER_OAUTH_SETUP.md`)
- **Service-level Authentication**: Individual service security
- **Traefik Middleware**: Centralized authentication enforcement

### Network Security
- **Tailscale VPN**: Primary access method
- **Network Isolation**: Services communicate through dedicated network
- **HTTPS Enforcement**: Automatic HTTP to HTTPS redirect

### Configuration Security
- **No Default Passwords**: Secure defaults across all services
- **API Token Management**: Scoped tokens for external services
- **Certificate Automation**: Automated SSL certificate management

## Service-Specific Details

### Portainer Configuration
- **Docker Socket Access**: Full Docker management capabilities
- **OAuth Integration**: Post-deployment JumpCloud configuration
- **Volume Persistence**: Configuration stored in named volume

### Traefik Features
- **Dynamic Configuration**: File provider for custom configurations
- **Service Discovery**: Automatic Docker service detection
- **Load Balancing**: Built-in load balancing capabilities
- **Middleware Support**: Authentication, rate limiting, headers

### Pi-hole Integration
- **Gateway DNS**: Configured as upstream DNS for network gateway
- **Ad Blocking**: Automatic blocklist updates
- **Web Interface**: Traefik-proxied admin interface
- **Network Binding**: Specific IP binding to avoid conflicts

### Media Stack (*arr)
- **Complete Automation**: End-to-end media management
- **Quality Management**: Automated quality profiles via Recyclarr
- **Download Management**: Automated cleanup via qbit_manage
- **Storage Integration**: Flexible local and NFS storage support

## Configuration Files

### Core Infrastructure
- `/docker-compose.yml` - Portainer management service
- `/traefik/docker-compose.yml` - Reverse proxy configuration
- `/traefik/dynamic/tls.yml` - TLS security settings
- `/.env.example` - Main environment template

### Service Configuration
- `/pihole/docker-compose.yml` - DNS service configuration
- `/arr/docker-compose.yml` - Media management suite
- `/arr/qbit-manage-config.yml` - Download cleanup configuration

### Documentation
- `/README.md` - Primary documentation
- `/PORTAINER_OAUTH_SETUP.md` - OAuth configuration guide
- `/traefik/README.md` - Traefik service documentation
- `/pihole/README.md` - Pi-hole service documentation
- `/arr/README.md` - Media stack documentation

## Common Commands

### Prerequisites
```bash
# Always create the external network first (only needed once)
docker network create stacksmith
```

### Service Management
```bash
# Deploy specific service
docker compose -f traefik/docker-compose.yml up -d

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

## Operational Patterns

### Volume Management
- **Named Volumes**: Persistent data storage
- **Backup Strategy**: Volume backup procedures documented per service
- **Configuration Persistence**: Service configuration stored in volumes

### Monitoring and Maintenance
- **Health Checks**: Container health monitoring
- **Log Management**: Structured logging with configurable levels
- **Resource Monitoring**: Built-in Docker stats and Portainer monitoring

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
   - Use `websecure-tailscale` entrypoint
   - Include required Traefik labels
   - Set correct service port
6. Use consistent naming: `stacksmith_servicename`
7. Join `stacksmith` external network
8. Include standard environment variables (PUID, PGID, TZ)

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