# Traefik Reverse Proxy Service

Traefik reverse proxy with automatic HTTPS via Let's Encrypt and Cloudflare DNS challenge. Provides routing, SSL termination, and authentication middleware for all services.

## Service Overview

- **Image**: `traefik:latest`
- **Purpose**: Reverse proxy, load balancer, and SSL termination
- **Ports**: 80 (HTTP), 443 (HTTPS)
- **Network**: Creates `traefik` network for other services

## Dependencies

**Required Services**: None (standalone service)

**Optional Integrations**:
- **JumpCloud Auth**: Provides authentication middleware (`jumpcloud-auth@docker`)
- **Any web service**: Can be proxied through Traefik

## Configuration

### Environment Variables

Copy and configure the environment file:
```bash
cp .env.example .env
```

**Required Variables**:
- `TRAEFIK_HOSTNAME`: Hostname for Traefik dashboard (e.g., `proxy.example.com`)
- `ACME_EMAIL`: Email for Let's Encrypt certificates
- `CLOUDFLARE_DNS_API_TOKEN`: Cloudflare API token for DNS challenge

**Optional Variables**:
- `TRAEFIK_INTERFACE`: Network interface binding (default: `0.0.0.0`)
- `JUMPCLOUD_AUTH_HOST`: JumpCloud auth container name (default: `jumpcloud-auth`)
- `JUMPCLOUD_AUTH_HOSTNAME`: JumpCloud auth hostname (e.g., `auth.example.com`)

### Cloudflare API Token

1. Login to Cloudflare Dashboard
2. Go to **My Profile** → **API Tokens**
3. Create token with:
   - **Zone:Zone:Read**
   - **Zone:DNS:Edit**
   - **Zone Resources**: Include your domain

## Deployment

### Standalone Deployment
```bash
# Configure environment
cp .env.example .env
# Edit .env with your settings

# Create external network
docker network create stacksmith

# Deploy Traefik
docker compose up -d
```

### With JumpCloud Authentication
```bash
# Create external network
docker network create stacksmith

# Deploy Traefik + JumpCloud auth
docker compose -f docker-compose.yml -f ../jumpcloud/docker-compose.yml up -d
```

### With Other Services
```bash
# Create external network (if not already created)
docker network create stacksmith

# Deploy management stack (Portainer + Traefik)
docker compose -f ../docker-compose.yml -f docker-compose.yml up -d

# Deploy Pi-hole with Traefik
docker compose -f docker-compose.yml -f ../pihole/docker-compose.yml up -d
```

## Service Integration

### Adding Services to Traefik

Services can be added to Traefik by:

1. **Joining the network**:
   ```yaml
   networks:
     - stacksmith
   ```

2. **Adding labels**:
   ```yaml
   labels:
     - "traefik.enable=true"
     - "traefik.http.routers.service-name.rule=Host(`service.example.com`)"
     - "traefik.http.routers.service-name.entrypoints=websecure"
     - "traefik.http.routers.service-name.tls.certresolver=stacksmith"
   ```

3. **Optional authentication**:
   ```yaml
   labels:
     - "traefik.http.routers.service-name.middlewares=jumpcloud-auth@docker"
   ```

### Available Middlewares

- `jumpcloud-auth@docker`: JumpCloud authentication (requires JumpCloud service)

## Accessing Services

### Traefik Dashboard
- **URL**: `https://proxy.example.com` (or your configured hostname)
- **Authentication**: JumpCloud OAuth (if enabled)
- **Features**: Route monitoring, service health, SSL certificate status

### Monitoring
```bash
# View Traefik logs
docker compose logs -f traefik

# Check service status
docker compose ps

# View network
docker network ls | grep traefik
```

## Troubleshooting

### Common Issues

**SSL Certificate Issues**:
```bash
# Check certificate storage
docker volume inspect traefik_traefik-certificates

# Verify Cloudflare API token
docker compose logs traefik | grep cloudflare
```

**Service Discovery Issues**:
```bash
# Verify Docker socket access
docker compose exec traefik ls -la /var/run/docker.sock

# Check Traefik configuration
docker compose exec traefik cat /etc/traefik/traefik.yml
```

**Network Connectivity**:
```bash
# List Stacksmith network members
docker network inspect stacksmith

# Test service connectivity
docker compose exec traefik nslookup [service-name]
```

### Debug Mode

Enable debug logging by adding to docker-compose.yml:
```yaml
command:
  - --log.level=DEBUG
  - --accesslog=true
```

## Security Considerations

- **Cloudflare API Token**: Use scoped tokens with minimal permissions
- **Docker Socket**: Mounted read-only for security
- **Network Isolation**: Services communicate through Traefik network
- **HTTPS Only**: HTTP automatically redirects to HTTPS
- **Authentication**: JumpCloud middleware protects sensitive services

## Advanced Configuration

### Custom Dynamic Configuration

Add custom configuration files to the `dynamic/` directory:
```yaml
# dynamic/middleware.yml
http:
  middlewares:
    custom-headers:
      headers:
        customRequestHeaders:
          X-Custom-Header: "value"
```

### Multiple Domains

Configure multiple certificate resolvers for different domains:
```yaml
command:
  - --certificatesresolvers.domain2.acme.dnschallenge.provider=route53
```

This service provides the foundation for all web services in the stacksmith architecture.