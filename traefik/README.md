# Traefik Reverse Proxy Service

Reverse proxy with automatic HTTPS via Let's Encrypt and Cloudflare DNS challenge.

## Features
- **Automatic SSL**: Let's Encrypt certificates with DNS challenge
- **Service Discovery**: Automatic routing based on Docker labels
- **Load Balancing**: Built-in load balancing
- **Tailscale Integration**: Primary access via Tailscale VPN

## Configuration

```bash
cp traefik/.env.example traefik/.env
# Edit with your hostname, email, and Cloudflare API token
```

### Cloudflare API Token
Create token with Zone:Zone:Read and Zone:DNS:Edit permissions for your domain.

## Deployment

```bash
docker network create stacksmith
docker compose -f traefik/docker-compose.yml up -d
```

## Service Integration

Services join the `stacksmith` network and use Docker labels for automatic discovery:

```yaml
networks:
  - stacksmith
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.service-name.rule=Host(`service.example.com`)"
  - "traefik.http.routers.service-name.entrypoints=websecure"
  - "traefik.http.routers.service-name.tls.certresolver=stacksmith"
```

**Tailscale entrypoint**: Services use `websecure-tailscale` for VPN access.

## Dashboard

Access dashboard at your configured hostname. Features route monitoring, service health, and SSL certificate status.

Provides automatic service discovery, SSL termination, and authentication middleware for all Stacksmith services.