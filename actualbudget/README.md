# Actual Budget - Personal Finance Management

Actual Budget is a local-first personal finance tool based on zero-based budgeting principles. It provides a modern, privacy-focused alternative to cloud-based budgeting services.

## Service Overview

- **Image**: `actualbudget/actual-server:latest`
- **Purpose**: Personal finance management and budgeting
- **Port**: 5006 (Web interface via Traefik)
- **Network**: Traefik network for reverse proxy integration
- **Access**: Tailscale VPN only (secure entrypoint)

## Features

- **Zero-based budgeting**: Assign every dollar a purpose
- **Local-first**: All data stored locally, no cloud dependency
- **Bank sync**: Optional bank synchronization capabilities
- **Multi-device**: Web-based interface accessible from any device
- **Import/Export**: Support for various file formats
- **Privacy-focused**: No data sharing with third parties

## Prerequisites

1. **Traefik**: The reverse proxy must be configured and running
2. **Tailscale**: VPN access required for secure connectivity
3. **External Network**: `stacksmith` network must exist

## Configuration

### Environment Variables

Copy `actualbudget/.env.example` to `actualbudget/.env` and configure:

```bash
# Actual Budget Configuration
ACTUALBUDGET_HOSTNAME=fin.example.com

# User/Group IDs (match your system user)
PUID=1000
PGID=1000

# Timezone
TZ=Europe/Zurich
```

### Required Configuration

**Hostname Configuration**:
- Set `ACTUALBUDGET_HOSTNAME` to your desired domain
- Ensure DNS points to your Tailscale IP
- Certificate will be automatically generated via Let's Encrypt

**User/Group IDs**:
- Match `PUID` and `PGID` to your system user for proper file permissions
- Use `id` command to find your user and group IDs

## Deployment

### Prerequisites Setup
```bash
# Create external network (if not already created)
docker network create stacksmith

# Ensure Traefik is running
docker compose -f traefik/docker-compose.yml up -d
```

### Deploy Actual Budget
```bash
# Configure environment
cp actualbudget/.env.example actualbudget/.env
# Edit actualbudget/.env with your settings

# Deploy service
docker compose -f actualbudget/docker-compose.yml up -d

# Or deploy with other services
docker compose -f traefik/docker-compose.yml -f actualbudget/docker-compose.yml up -d
```

## Accessing the Service

### Web Interface
- **URL**: `https://fin.example.com` (or your configured hostname)
- **Access**: Tailscale VPN required
- **Initial Setup**: Create admin user on first access

### First-Time Setup

1. **Access Service**: Navigate to your configured hostname
2. **Import Data** (optional): Import existing financial data
3. **Create Budget**: Set up your first budget
4. **Configure Accounts**: Add your financial accounts
5. **Set Categories**: Create spending categories

## Service Management

### Container Operations
```bash
# View Actual Budget logs
docker compose -f actualbudget/docker-compose.yml logs -f

# Restart service
docker compose -f actualbudget/docker-compose.yml restart

# Update service
docker compose -f actualbudget/docker-compose.yml pull
docker compose -f actualbudget/docker-compose.yml up -d

# Stop service
docker compose -f actualbudget/docker-compose.yml down
```

### Data Management
```bash
# Backup Actual Budget data
docker run --rm -v actualbudget-data:/data -v $(pwd):/backup alpine tar czf /backup/actualbudget-backup.tar.gz /data

# Restore Actual Budget data
docker run --rm -v actualbudget-data:/data -v $(pwd):/backup alpine tar xzf /backup/actualbudget-backup.tar.gz -C /
```

## Security Considerations

- **Tailscale Only**: Service only accessible via Tailscale VPN
- **Local Data**: All financial data stored locally, not in cloud
- **HTTPS**: Automatic SSL certificate via Let's Encrypt
- **File Permissions**: Proper user/group ID configuration
- **Regular Backups**: Backup data volume regularly

## Troubleshooting

### Common Issues

**Service Not Accessible**:
```bash
# Check container status
docker compose -f actualbudget/docker-compose.yml ps

# Check container logs
docker compose -f actualbudget/docker-compose.yml logs actualbudget

# Verify Traefik routing
docker compose -f traefik/docker-compose.yml logs traefik | grep actualbudget
```

**Permission Issues**:
```bash
# Check volume permissions
docker compose -f actualbudget/docker-compose.yml exec actualbudget ls -la /data

# Verify PUID/PGID settings
docker compose -f actualbudget/docker-compose.yml exec actualbudget id
```

**Network Connectivity**:
```bash
# Test network connectivity
docker compose -f actualbudget/docker-compose.yml exec actualbudget ping traefik

# Check network configuration
docker network inspect stacksmith | grep actualbudget
```

### Debug Commands

```bash
# Access container shell
docker compose -f actualbudget/docker-compose.yml exec actualbudget sh

# Check service health
docker compose -f actualbudget/docker-compose.yml exec actualbudget wget -qO- http://localhost:5006/health || echo "Health check failed"

# Monitor resource usage
docker stats stacksmith_actualbudget
```

## Integration

### Backup Integration
- **Automated Backups**: Schedule regular data backups
- **Cloud Sync**: Optional sync of backup files to cloud storage
- **Version Control**: Keep multiple backup versions

### Monitoring Integration  
- **Health Checks**: Container health monitoring
- **Log Aggregation**: Centralized logging
- **Alerting**: Set up alerts for service failures

## Data Import/Export

### Supported Formats
- **CSV**: Bank statements and transaction data
- **QIF**: Quicken Interchange Format
- **OFX**: Open Financial Exchange
- **Manual Entry**: Direct transaction input

### Export Options
- **CSV Export**: Transaction and budget data
- **Backup Files**: Complete database backup
- **Reports**: PDF and Excel reports

This service provides a comprehensive personal finance management solution with privacy-first principles and local data storage.