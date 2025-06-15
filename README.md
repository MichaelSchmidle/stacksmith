# Stacksmith - Portainer Management Service

Docker stack management system with Portainer for container orchestration. Provides a web-based management interface for Docker environments with optional reverse proxy and authentication integration.

## Service Overview

- **Image**: `portainer/portainer-ce:latest`
- **Purpose**: Docker container management and orchestration
- **Port**: 9000 (Web interface via Traefik)
- **Network**: Traefik network for reverse proxy integration
- **Authentication**: JumpCloud OAuth (post-deployment configuration)

## Architecture

Stacksmith provides a flexible Docker stack management system with decoupled service deployment:

- **Management Environment**: Runs Portainer (this service)
- **Reverse Proxy**: Traefik with automatic HTTPS
- **Authentication**: JumpCloud OAuth integration
- **DNS Services**: Pi-hole for ad-blocking
- **Flexible Deployment**: Services deployed where operationally optimal

## Dependencies

**Optional Services**:
- **Traefik**: Provides reverse proxy and HTTPS termination
- **JumpCloud Auth**: Provides external authentication (configured via web UI)

**External Dependencies**:
- **Docker**: Container runtime
- **Docker Compose**: Container orchestration

## Configuration

### Environment Variables

Copy and configure the environment file:
```bash
cp .env.example .env
```

**Required Variables**:
- `PORTAINER_HOSTNAME`: Hostname for Portainer web interface (e.g., `mgmt.example.com`)

**Optional Variables**:
- `LOG_LEVEL`: Container logging level (default: `DEBUG` for OAuth troubleshooting)

### Docker Socket Access

Portainer requires access to the Docker socket for container management:
- **Socket Mount**: `/var/run/docker.sock:/var/run/docker.sock`
- **Security**: Read-write access required for container management
- **Permissions**: Ensure Docker socket is accessible

## Deployment

### Standalone Deployment (No Reverse Proxy)
```bash
# Configure environment
cp .env.example .env
# Edit .env with your settings

# Deploy Portainer only
docker compose up -d

# Access via: http://localhost:9000
```

### With Traefik Reverse Proxy
```bash
# Deploy Portainer with Traefik
docker compose -f docker-compose.yml -f traefik/docker-compose.yml up -d

# Access via: https://mgmt.example.com
```

### With Full Authentication Stack
```bash
# Deploy complete management stack
docker compose -f docker-compose.yml -f traefik/docker-compose.yml -f jumpcloud/docker-compose.yml up -d
```

### Common Deployment Scenarios

**Home Lab Setup**:
```bash
# Management + Reverse Proxy
docker compose -f docker-compose.yml -f traefik/docker-compose.yml up -d
```

**Enterprise Setup**:
```bash
# Full stack with authentication
docker compose -f docker-compose.yml -f traefik/docker-compose.yml -f jumpcloud/docker-compose.yml up -d
```

**Multi-Environment Architecture**:
- **Management Environment**: `docker-compose.yml + traefik/docker-compose.yml`
- **Auth Environment**: `traefik/docker-compose.yml + jumpcloud/docker-compose.yml` (VPS)
- **Agent Environments**: `traefik/docker-compose.yml` (points to remote auth)

## Accessing Services

### Portainer Web Interface
- **URL**: `https://mgmt.example.com` (or configured hostname)
- **Initial Setup**: Create admin user on first access
- **Authentication**: Local admin + optional OAuth integration

### Initial Setup

1. **Access Portainer**: Navigate to your configured hostname
2. **Create Admin User**: Set username and password
3. **Connect Docker Environment**: Select local Docker socket
4. **Configure OAuth** (optional): See OAuth setup guide

## OAuth Configuration

Portainer OAuth must be configured through the web interface after deployment. See `PORTAINER_OAUTH_SETUP.md` for detailed JumpCloud integration instructions.

### Quick OAuth Setup

1. **Deploy Portainer**: Complete initial setup
2. **Access Settings**: Navigate to Settings → Authentication → OAuth
3. **Configure JumpCloud**:
   - Client ID: From JumpCloud application
   - Client Secret: From JumpCloud application
   - Authorization URL: `https://oauth.id.jumpcloud.com/oauth2/auth`
   - Access Token URL: `https://oauth.id.jumpcloud.com/oauth2/token`
   - Resource URL: `https://oauth.id.jumpcloud.com/userinfo`
   - Scopes: `openid profile email`

## Service Management

### Container Operations
```bash
# View Portainer logs
docker compose logs -f portainer

# Restart Portainer
docker compose restart portainer

# Update Portainer
docker compose pull portainer
docker compose up -d portainer
```

### Stack Management
```bash
# Deploy additional services
docker compose -f docker-compose.yml -f pihole/docker-compose.yml up -d

# Scale services
docker compose up -d --scale portainer=1

# Stop all services
docker compose down
```

### Backup and Restore
```bash
# Backup Portainer data
docker run --rm -v portainer-data:/data -v $(pwd):/backup alpine tar czf /backup/portainer-backup.tar.gz /data

# Restore Portainer data
docker run --rm -v portainer-data:/data -v $(pwd):/backup alpine tar xzf /backup/portainer-backup.tar.gz -C /
```

## Monitoring

### Portainer Health
```bash
# Check container status
docker compose ps portainer

# Monitor resource usage
docker stats portainer

# View container logs
docker compose logs --tail=100 portainer
```

### System Monitoring
- **Docker Environment**: Monitor through Portainer web interface
- **Container Statistics**: Real-time metrics in Portainer dashboard
- **Resource Usage**: CPU, memory, network, and storage metrics

## Environment Management

### Agent Deployment

Deploy Portainer agents on remote Docker hosts:

```bash
# Remote agent deployment
docker run -d \
  -p 9001:9001 \
  --name portainer_agent \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  portainer/agent:latest
```

### Environment Connection

1. **Add Environment**: Portainer UI → Environments → Add environment
2. **Select Agent**: Choose Docker agent
3. **Configure Connection**: Enter agent IP and port 9001
4. **Name Environment**: Provide descriptive name
5. **Connect**: Verify connection and start managing

## Troubleshooting

### Common Issues

**Portainer Won't Start**:
```bash
# Check Docker socket permissions
ls -la /var/run/docker.sock

# Verify volume mounts
docker inspect portainer | grep Mounts

# Check container logs
docker compose logs portainer
```

**Web Interface Not Accessible**:
```bash
# Test direct container access
curl http://localhost:9000

# Check Traefik routing
docker compose logs traefik | grep portainer

# Verify network connectivity
docker network inspect traefik | grep portainer
```

**OAuth Authentication Issues**:
- Verify JumpCloud application configuration
- Check redirect URI matches Portainer hostname
- Review OAuth setup documentation
- Enable debug logging (`LOG_LEVEL=DEBUG`)

### Debug Commands

```bash
# Check Portainer configuration
docker compose exec portainer cat /data/portainer.db

# Test network connectivity
docker compose exec portainer nslookup traefik

# Verify Docker socket access
docker compose exec portainer ls -la /var/run/docker.sock
```

## Security Considerations

- **Docker Socket**: Provides full Docker access - secure deployment environment
- **Admin Access**: Use strong passwords and enable OAuth when possible
- **Network Isolation**: Deploy behind reverse proxy for HTTPS
- **Authentication**: Configure JumpCloud OAuth for enterprise environments
- **Access Control**: Use Portainer's built-in user management and teams
- **Regular Updates**: Keep Portainer image updated for security patches

## Advanced Configuration

### Custom Themes
```bash
# Mount custom theme directory
volumes:
  - ./themes:/app/themes
```

### SSL Certificates
```bash
# Mount custom SSL certificates
volumes:
  - ./ssl:/certs
```

### Environment Variables
```bash
# Additional Portainer configuration
environment:
  - PORTAINER_ADMIN_PASSWORD_FILE=/run/secrets/portainer_password
```

## Integration with Other Services

### Traefik Integration
- **Automatic routing**: Based on hostname configuration
- **SSL termination**: Handled by Traefik
- **Middleware support**: Authentication, rate limiting, etc.

### JumpCloud Integration
- **OAuth authentication**: Enterprise identity management
- **User provisioning**: Automatic user creation
- **Group management**: Map JumpCloud groups to Portainer teams

### Monitoring Integration
- **Logs**: Aggregated through Docker logging drivers
- **Metrics**: Exportable to monitoring systems
- **Alerts**: Configured through Portainer webhooks

This service provides the central management interface for the entire stacksmith Docker infrastructure.