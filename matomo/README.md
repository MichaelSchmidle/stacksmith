# Matomo Analytics Stack

Matomo is a free and open-source web analytics platform that provides detailed insights into website traffic and user behavior. This stack provides a complete Matomo deployment with MariaDB database backend.

## Features

- **Open Source Analytics**: Privacy-focused alternative to Google Analytics
- **Complete Ownership**: All data stored locally on your infrastructure
- **Rich Reporting**: Comprehensive dashboards and reports
- **GDPR Compliant**: Built-in privacy features and compliance tools
- **Extensible**: Plugin ecosystem for additional functionality

## Services

- **Matomo**: Web analytics platform (`matomo:latest`)
- **MariaDB**: Database backend for analytics data (`mariadb:latest`)

## Quick Start

### Prerequisites

Ensure the external network exists:
```bash
docker network create stacksmith
```

### Environment Configuration

1. Copy the environment template:
```bash
cp matomo/.env.example matomo/.env
```

2. Edit `matomo/.env` with your configuration:
```bash
# Matomo Configuration
MATOMO_HOSTNAME=trck.yourdomain.com

# Database Configuration - Use strong passwords
MATOMO_DB_NAME=matomo
MATOMO_DB_USER=matomo
MATOMO_DB_PASSWORD=your_secure_password
MATOMO_DB_ROOT_PASSWORD=your_secure_root_password
```

### Deployment

Deploy the Matomo stack:
```bash
docker compose -f matomo/docker-compose.yml up -d
```

Deploy with Traefik (recommended):
```bash
docker compose -f traefik/docker-compose.yml -f matomo/docker-compose.yml up -d
```

## Initial Setup

1. **Access Matomo**: Navigate to your configured hostname (e.g., `https://trck.yourdomain.com`)

2. **Installation Wizard**: Complete the Matomo installation wizard:
   - Database configuration will be pre-filled
   - Create your admin user account
   - Add your first website to track

3. **Tracking Code**: Copy the tracking code and add it to your websites

4. **Configure**: Set up additional settings like:
   - Privacy settings and GDPR compliance
   - User permissions and access
   - Email reports and alerts

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MATOMO_HOSTNAME` | Hostname for web access | `trck.example.com` |
| `MATOMO_DB_NAME` | Database name | `matomo` |
| `MATOMO_DB_USER` | Database user | `matomo` |
| `MATOMO_DB_PASSWORD` | Database password | `secure_password_here` |
| `MATOMO_DB_ROOT_PASSWORD` | Database root password | `secure_root_password_here` |

### Volume Persistence

- **matomo-data**: Matomo application files and configuration
- **matomo-db-data**: MariaDB database files

### Network Configuration

- **stacksmith**: External network for Traefik integration
- **matomo-internal**: Internal network for database communication

## Traefik Integration

The service is pre-configured for Traefik with:
- Automatic service discovery
- HTTPS with Let's Encrypt certificates
- Tailscale network binding
- Host-based routing

## Backup and Maintenance

### Database Backup

```bash
# Create database backup
docker exec stacksmith_matomo_db mysqldump -u root -p${MATOMO_DB_ROOT_PASSWORD} matomo > matomo_backup.sql

# Restore database backup
docker exec -i stacksmith_matomo_db mysql -u root -p${MATOMO_DB_ROOT_PASSWORD} matomo < matomo_backup.sql
```

### Volume Backup

```bash
# Backup Matomo data
docker run --rm -v stacksmith_matomo_data:/data -v $(pwd):/backup alpine tar czf /backup/matomo_data_backup.tar.gz /data

# Backup database
docker run --rm -v stacksmith_matomo_db_data:/data -v $(pwd):/backup alpine tar czf /backup/matomo_db_backup.tar.gz /data
```

### Updates

```bash
# Update Matomo
docker compose -f matomo/docker-compose.yml pull
docker compose -f matomo/docker-compose.yml up -d

# Check logs
docker compose -f matomo/docker-compose.yml logs -f matomo
```

## Security Considerations

- **Strong Passwords**: Use strong, unique passwords for database access
- **Regular Updates**: Keep Matomo and MariaDB images updated
- **Access Control**: Configure user permissions appropriately
- **HTTPS Only**: Ensure all access is over HTTPS via Traefik
- **Database Security**: Database is isolated on internal network

## Troubleshooting

### Common Issues

**Matomo not accessible**:
- Check Traefik configuration and labels
- Verify hostname DNS resolution
- Check container logs: `docker logs stacksmith_matomo`

**Database connection errors**:
- Verify database environment variables
- Check database container status: `docker logs stacksmith_matomo_db`
- Ensure database is fully initialized before Matomo starts

**Performance issues**:
- Monitor database performance and optimize queries
- Consider increasing MariaDB memory limits
- Review Matomo performance settings

**Plugin issues**:
- Check Matomo logs for plugin errors
- Verify plugin compatibility with Matomo version
- Restart Matomo container after plugin changes

### Logs

```bash
# View Matomo logs
docker logs stacksmith_matomo -f

# View database logs
docker logs stacksmith_matomo_db -f

# View all stack logs
docker compose -f matomo/docker-compose.yml logs -f
```

## Integration Examples

### With other Stacksmith services

```bash
# Deploy with Traefik and Portainer
docker compose -f docker-compose.yml -f traefik/docker-compose.yml -f matomo/docker-compose.yml up -d

# Full analytics and media stack
docker compose -f traefik/docker-compose.yml -f matomo/docker-compose.yml -f arr/docker-compose.yml up -d
```

## Advanced Configuration

### Custom Matomo Configuration

Mount custom PHP configuration:
```yaml
volumes:
  - matomo-data:/var/www/html
  - ./custom-config.php:/var/www/html/config/config.ini.php:ro
```

### Database Tuning

Customize MariaDB for analytics workload:
```yaml
command: 
  - --max-allowed-packet=64MB
  - --innodb-buffer-pool-size=512M
  - --query-cache-size=32M
```

### SSL/TLS Configuration

The service uses Traefik for SSL termination with automatic Let's Encrypt certificates. No additional SSL configuration is required.

## Monitoring

Monitor Matomo performance through:
- Built-in Matomo diagnostics (Settings > System Check)
- Database performance metrics via Portainer
- Container resource usage monitoring
- Log analysis for errors and performance issues

This Matomo stack provides a complete, privacy-focused web analytics solution that integrates seamlessly with the Stacksmith infrastructure.