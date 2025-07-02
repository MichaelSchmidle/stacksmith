# Uptime Kuma Monitoring Stack

Uptime Kuma is a self-hosted monitoring tool that provides real-time website and service uptime monitoring with a beautiful web interface. It offers comprehensive monitoring capabilities including HTTP/HTTPS, TCP, DNS, and more.

## Features

- **Real-time Monitoring**: Monitor websites, APIs, and services
- **Beautiful Dashboard**: Clean, intuitive web interface
- **Multiple Monitor Types**: HTTP/HTTPS, TCP, Ping, DNS, and more
- **Notifications**: Support for 90+ notification services
- **Status Pages**: Public status pages for your services
- **Multi-language Support**: Available in 30+ languages
- **Mobile Responsive**: Works on all devices

## Services

- **Uptime Kuma**: Monitoring application (`louislam/uptime-kuma:1`)

## Quick Start

### Prerequisites

Ensure the external network exists:
```bash
docker network create stacksmith
```

### Environment Configuration

1. Copy the environment template:
```bash
cp uptimekuma/.env.example uptimekuma/.env
```

2. Edit `uptimekuma/.env` with your configuration:
```bash
# Uptime Kuma Configuration
UPTIME_KUMA_HOSTNAME=mon.yourdomain.com
```

### Deployment

Deploy the Uptime Kuma stack:
```bash
docker compose -f uptimekuma/docker-compose.yml up -d
```

Deploy with Traefik (recommended):
```bash
docker compose -f traefik/docker-compose.yml -f uptimekuma/docker-compose.yml up -d
```

## Initial Setup

1. **Access Uptime Kuma**: Navigate to your configured hostname (e.g., `https://mon.yourdomain.com`)

2. **Create Admin Account**: Set up your administrator account on first access

3. **Add Monitors**: Start adding monitors for your services:
   - HTTP/HTTPS websites
   - TCP services
   - Ping monitors
   - DNS queries

4. **Configure Notifications**: Set up notification channels:
   - Email, Slack, Discord
   - Telegram, PagerDuty
   - Webhooks and more

5. **Create Status Pages**: Optional public status pages for your services

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `UPTIME_KUMA_HOSTNAME` | Hostname for web access | `mon.example.com` |

### Volume Persistence

- **uptime-kuma-data**: Application data, configuration, and monitoring history

### Network Configuration

- **stacksmith**: External network for Traefik integration
- **Port 3001**: Internal application port (proxied by Traefik)

### Storage Requirements

**Important**: Uptime Kuma requires local storage and does **NOT** support NFS (Network File System). Ensure the volume is mounted on local disk.

## Traefik Integration

The service is pre-configured for Traefik with:
- Automatic service discovery
- HTTPS with Let's Encrypt certificates
- Tailscale network binding
- Host-based routing

## Monitor Types

### HTTP/HTTPS Monitoring
- Website availability
- Response time tracking
- Status code validation
- Content validation

### TCP Monitoring
- Port connectivity
- Service availability
- Connection time tracking

### Ping Monitoring
- Network connectivity
- Latency monitoring
- Packet loss detection

### DNS Monitoring
- DNS resolution validation
- Response time tracking
- Record validation

## Backup and Maintenance

### Data Backup

```bash
# Backup Uptime Kuma data
docker run --rm -v stacksmith_uptime_kuma_data:/data -v $(pwd):/backup alpine tar czf /backup/uptime_kuma_backup.tar.gz /data

# Restore Uptime Kuma data
docker run --rm -v stacksmith_uptime_kuma_data:/data -v $(pwd):/backup alpine tar xzf /backup/uptime_kuma_backup.tar.gz -C /
```

### Updates

```bash
# Update Uptime Kuma
docker compose -f uptime-kuma/docker-compose.yml pull
docker compose -f uptimekuma/docker-compose.yml up -d

# Check logs
docker compose -f uptime-kuma/docker-compose.yml logs -f uptime-kuma
```

### Database Maintenance

Uptime Kuma uses SQLite for data storage. The database is automatically maintained, but you can:

- Monitor database size in the admin interface
- Configure data retention policies
- Export/import configurations

## Security Considerations

- **Access Control**: Configure user accounts and permissions
- **HTTPS Only**: Ensure all access is over HTTPS via Traefik
- **API Security**: Secure API keys if using external integrations
- **Regular Updates**: Keep Uptime Kuma updated for security patches

## Troubleshooting

### Common Issues

**Uptime Kuma not accessible**:
- Check Traefik configuration and labels
- Verify hostname DNS resolution
- Check container logs: `docker logs stacksmith_uptime_kuma`

**Monitors not working**:
- Verify network connectivity from container
- Check monitor configuration settings
- Review monitor logs in the web interface

**Data persistence issues**:
- Ensure volume is properly mounted
- Verify local storage (not NFS) is being used
- Check container permissions

**Performance issues**:
- Monitor resource usage
- Adjust monitoring intervals
- Consider database cleanup

### Logs

```bash
# View Uptime Kuma logs
docker logs stacksmith_uptime_kuma -f

# View all stack logs
docker compose -f uptime-kuma/docker-compose.yml logs -f
```

## Integration Examples

### With other Stacksmith services

```bash
# Deploy with Traefik and Portainer
docker compose -f docker-compose.yml -f traefik/docker-compose.yml -f uptime-kuma/docker-compose.yml up -d

# Full monitoring and infrastructure stack
docker compose -f traefik/docker-compose.yml -f uptime-kuma/docker-compose.yml -f pihole/docker-compose.yml up -d
```

### Monitor Stacksmith Services

Use Uptime Kuma to monitor your other Stacksmith services:

- **Portainer**: Monitor management interface availability
- **Pi-hole**: Monitor DNS service and web interface
- **Media Services**: Monitor *arr applications
- **External Services**: Monitor internet connectivity and external APIs

## Advanced Configuration

### Custom Notifications

Configure advanced notification rules:
- Escalation policies
- Maintenance windows
- Group notifications
- Custom webhook integrations

### Status Pages

Create public status pages:
- Custom branding
- Service grouping
- Incident management
- Subscriber notifications

### API Integration

Use the Uptime Kuma API for:
- Automated monitor creation
- Status retrieval
- Integration with other tools

## Monitoring Best Practices

### Monitor Configuration
- Set appropriate check intervals
- Configure retry attempts
- Set realistic timeout values
- Use descriptive monitor names

### Notification Strategy
- Avoid notification spam
- Set up escalation chains
- Use different channels for different severity levels
- Test notification channels regularly

### Performance Optimization
- Monitor resource usage
- Adjust check frequencies based on service criticality
- Regular database maintenance
- Archive old monitoring data

This Uptime Kuma stack provides comprehensive monitoring capabilities that integrate seamlessly with the Stacksmith infrastructure, offering real-time visibility into service health and availability.