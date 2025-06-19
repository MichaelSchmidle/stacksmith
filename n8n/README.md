# n8n - Workflow Automation Platform

n8n is a free and open-source workflow automation tool that allows you to connect different services and automate tasks without coding. It provides a visual workflow editor with a wide range of integrations.

## Service Overview

- **Image**: `n8nio/n8n:latest`
- **Purpose**: Workflow automation and integration platform
- **Port**: 5678 (Web interface via Traefik)
- **Network**: Traefik network for reverse proxy integration
- **Access**: Tailscale VPN only (secure entrypoint)

## Features

- **Visual Workflow Editor**: Drag-and-drop interface for creating automations
- **400+ Integrations**: Connect to popular services and APIs  
- **Self-hosted**: Complete control over your automation workflows
- **Custom Nodes**: Extensible with custom functionality
- **Scheduling**: Time-based and event-driven automation
- **Data Processing**: Transform and manipulate data between services
- **Webhook Support**: HTTP endpoints for external integrations

## Prerequisites

1. **Traefik**: The reverse proxy must be configured and running
2. **Tailscale**: VPN access required for secure connectivity
3. **External Network**: `stacksmith` network must exist

## Configuration

### Environment Variables

Copy `n8n/.env.example` to `n8n/.env` and configure:

```bash
# n8n Automation Configuration
N8N_HOSTNAME=auto.example.com

# User/Group IDs (match your system user)
PUID=1000
PGID=1000

# Timezone
TZ=Europe/Zurich
```

### Required Configuration

**Hostname Configuration**:
- Set `N8N_HOSTNAME` to your desired domain
- Ensure DNS points to your Tailscale IP
- Certificate will be automatically generated via Let's Encrypt

**User/Group IDs**:
- Match `PUID` and `PGID` to your system user for proper file permissions
- Use `id` command to find your user and group IDs

### Advanced Configuration

n8n supports additional environment variables for advanced configuration:

```bash
# Authentication (optional)
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=secure-password

# Database (default: SQLite)
DB_TYPE=sqlite
DB_SQLITE_DATABASE=/home/node/.n8n/database.sqlite

# Security
N8N_SECURE_COOKIE=true
N8N_DISABLE_PRODUCTION_MAIN_PROCESS=false
```

## Deployment

### Prerequisites Setup
```bash
# Create external network (if not already created)
docker network create stacksmith

# Ensure Traefik is running
docker compose -f traefik/docker-compose.yml up -d
```

### Deploy n8n
```bash
# Configure environment
cp n8n/.env.example n8n/.env
# Edit n8n/.env with your settings

# Deploy service
docker compose -f n8n/docker-compose.yml up -d

# Or deploy with other services
docker compose -f traefik/docker-compose.yml -f n8n/docker-compose.yml up -d
```

## Accessing the Service

### Web Interface
- **URL**: `https://auto.example.com` (or your configured hostname)
- **Access**: Tailscale VPN required
- **Initial Setup**: Create owner account on first access

### First-Time Setup

1. **Access Service**: Navigate to your configured hostname
2. **Create Owner Account**: Set up the initial administrator account
3. **Configure Settings**: Set up basic preferences and security settings
4. **Create First Workflow**: Start with a simple automation
5. **Connect Services**: Add credentials for external services

## Common Use Cases

### Home Automation
- **Smart Home Integration**: Connect IoT devices and services
- **Notifications**: Send alerts via email, Slack, or mobile push
- **Monitoring**: Automate system health checks and alerts

### Business Automation
- **Data Synchronization**: Keep databases and services in sync
- **Lead Processing**: Automate customer onboarding workflows
- **Report Generation**: Automated data collection and reporting
- **Social Media**: Schedule posts and monitor mentions

### Personal Productivity
- **Email Processing**: Filter and organize emails automatically
- **Calendar Integration**: Sync events across multiple calendars
- **File Management**: Automated backup and organization
- **Weather & News**: Daily briefings and alerts

## Service Management

### Container Operations
```bash
# View n8n logs
docker compose -f n8n/docker-compose.yml logs -f

# Restart service
docker compose -f n8n/docker-compose.yml restart

# Update service
docker compose -f n8n/docker-compose.yml pull
docker compose -f n8n/docker-compose.yml up -d

# Stop service
docker compose -f n8n/docker-compose.yml down
```

### Data Management
```bash
# Backup n8n data
docker run --rm -v n8n-data:/data -v $(pwd):/backup alpine tar czf /backup/n8n-backup.tar.gz /data

# Restore n8n data
docker run --rm -v n8n-data:/data -v $(pwd):/backup alpine tar xzf /backup/n8n-backup.tar.gz -C /
```

### Workflow Management
```bash
# Export workflows (via n8n CLI in container)
docker compose -f n8n/docker-compose.yml exec n8n n8n export:workflow --all --output=/data/workflows-backup.json

# Import workflows
docker compose -f n8n/docker-compose.yml exec n8n n8n import:workflow --input=/data/workflows-backup.json
```

## Security Considerations

- **Tailscale Only**: Service only accessible via Tailscale VPN
- **HTTPS**: Automatic SSL certificate via Let's Encrypt
- **Webhook Security**: Use authentication for webhook endpoints
- **Credential Storage**: Secure credential management within n8n
- **File Permissions**: Proper user/group ID configuration
- **Regular Backups**: Backup workflows and data regularly

## Integration Examples

### Popular Integrations
- **Communication**: Slack, Discord, Microsoft Teams, Email
- **Cloud Storage**: Google Drive, Dropbox, OneDrive
- **Databases**: MySQL, PostgreSQL, MongoDB
- **APIs**: REST APIs, GraphQL, HTTP Request nodes
- **File Processing**: CSV, JSON, XML manipulation
- **Monitoring**: Prometheus, Grafana, custom metrics

### Custom Webhooks
```javascript
// Example webhook payload processing
const payload = $input.all();
const processedData = payload.map(item => ({
  timestamp: new Date().toISOString(),
  data: item.json,
  source: 'webhook'
}));
return processedData;
```

## Troubleshooting

### Common Issues

**Service Not Accessible**:
```bash
# Check container status
docker compose -f n8n/docker-compose.yml ps

# Check container logs
docker compose -f n8n/docker-compose.yml logs n8n

# Verify Traefik routing
docker compose -f traefik/docker-compose.yml logs traefik | grep n8n
```

**Workflow Execution Issues**:
```bash
# Check n8n logs for workflow errors
docker compose -f n8n/docker-compose.yml logs n8n | grep ERROR

# Access container for debugging
docker compose -f n8n/docker-compose.yml exec n8n sh

# Test webhook endpoints
curl -X POST https://auto.example.com/webhook/test
```

**Permission Issues**:
```bash
# Check volume permissions
docker compose -f n8n/docker-compose.yml exec n8n ls -la /home/node/.n8n

# Verify PUID/PGID settings
docker compose -f n8n/docker-compose.yml exec n8n id
```

### Debug Commands

```bash
# Access n8n CLI
docker compose -f n8n/docker-compose.yml exec n8n n8n --help

# Check n8n version
docker compose -f n8n/docker-compose.yml exec n8n n8n --version

# Monitor resource usage
docker stats stacksmith_n8n

# Test internal connectivity
docker compose -f n8n/docker-compose.yml exec n8n wget -qO- http://localhost:5678/healthz
```

## Advanced Configuration

### Custom Nodes
```bash
# Install community nodes
docker compose -f n8n/docker-compose.yml exec n8n npm install n8n-nodes-custom-package

# Restart to load new nodes
docker compose -f n8n/docker-compose.yml restart n8n
```

### Environment Variables
```yaml
# Additional n8n configuration options
environment:
  - N8N_ENCRYPTION_KEY=your-encryption-key
  - N8N_USER_MANAGEMENT_DISABLED=false
  - N8N_PUBLIC_API_DISABLED=false
  - N8N_METRICS=true
```

## Monitoring and Maintenance

### Health Monitoring
- **Health Endpoint**: `/healthz` for container health checks
- **Metrics**: Built-in Prometheus metrics support
- **Log Analysis**: Structured logging for workflow monitoring

### Performance Optimization
- **Workflow Efficiency**: Optimize node execution order
- **Error Handling**: Implement proper error handling in workflows
- **Resource Limits**: Monitor CPU and memory usage
- **Database Maintenance**: Regular SQLite database optimization

## Backup Strategy

### What to Backup
- **Workflows**: Complete workflow definitions and configurations
- **Credentials**: Encrypted credential store
- **Settings**: Instance configuration and preferences
- **Execution History**: Workflow execution logs (optional)

### Backup Schedule
```bash
# Daily backup script example
#!/bin/bash
DATE=$(date +%Y%m%d)
docker run --rm -v n8n-data:/data -v /backup:/backup alpine tar czf /backup/n8n-$DATE.tar.gz /data
find /backup -name "n8n-*.tar.gz" -mtime +30 -delete
```

This service provides a powerful automation platform for connecting services and automating workflows with a user-friendly visual interface.