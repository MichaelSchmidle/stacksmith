# Duplicati Backup Service

Duplicati is a free, open-source backup client that securely stores encrypted, incremental, compressed backups on cloud storage services and remote file servers. This service provides a web-based interface for managing backup jobs and monitoring backup operations.

## Features

- **Encrypted Backups**: All backups are encrypted using AES-256 encryption
- **Incremental Backups**: Only backs up changed files to save space and time
- **Compression**: Reduces backup size with built-in compression
- **Multiple Storage Backends**: Supports cloud storage (Google Drive, OneDrive, S3, etc.) and remote servers
- **Web Interface**: Easy-to-use web-based management interface
- **Scheduling**: Automated backup scheduling with flexible timing options
- **Restore Capabilities**: Easy file and folder restoration from backups

## Quick Start

### Prerequisites

1. Ensure the `stacksmith` Docker network exists:
   ```bash
   docker network create stacksmith
   ```

2. Have Traefik running for SSL termination and routing

### Environment Setup

1. Copy the environment template:
   ```bash
   cp duplicati/.env.example duplicati/.env
   ```

2. Edit the environment file with your specific configuration:
   ```bash
   nano duplicati/.env
   ```

3. Configure the required variables:
   - `DUPLICATI_HOSTNAME`: Domain name for the web interface
   - `DUPLICATI_WEBSERVICE_PASSWORD`: Secure password for web UI access
   - `DUPLICATI_SOURCE_PATH`: Path to data you want to backup

### Deployment

Deploy Duplicati with the following command:

```bash
docker compose -f duplicati/docker-compose.yml up -d
```

Or deploy with other stacksmith services:

```bash
docker compose -f docker-compose.yml -f traefik/docker-compose.yml -f duplicati/docker-compose.yml up -d
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DUPLICATI_HOSTNAME` | Domain name for web interface | `backup.example.com` | Yes |
| `DUPLICATI_WEBSERVICE_PASSWORD` | Web UI password | - | Recommended |
| `DUPLICATI_SOURCE_PATH` | Path to source data for backup | `/path/to/your/data` | Yes |
| `PUID` | User ID for file permissions | `1000` | Yes |
| `PGID` | Group ID for file permissions | `1000` | Yes |
| `TZ` | Timezone | `America/New_York` | Yes |

### Volume Configuration

- **duplicati-config**: Stores Duplicati configuration and database
- **duplicati-backupss**: Local backup storage location
- **Source Mount**: Read-only mount of data to be backed up

### Network Configuration

- **Port**: 8200 (internal, proxied via Traefik)
- **Network**: Joins the `stacksmith` external network
- **Access**: Via Traefik reverse proxy with SSL termination

## Usage

### Initial Setup

1. Access the web interface at `https://your-duplicati-hostname`
2. Set up your first backup job:
   - Choose backup destination (cloud storage or local)
   - Select source files/folders from `/source`
   - Configure encryption password
   - Set backup schedule

### Backup Destinations

Duplicati supports numerous backup destinations:

- **Cloud Storage**: Google Drive, OneDrive, Dropbox, Box, Amazon S3, etc.
- **Remote Servers**: FTP, SFTP, WebDAV, etc.
- **Local Storage**: Use the `/backups` volume for local storage

### Best Practices

1. **Use Strong Encryption**: Always set a strong encryption passphrase
2. **Test Restores**: Regularly test restore operations
3. **Monitor Backups**: Check backup job status regularly
4. **Backup Configuration**: Export your Duplicati configuration for disaster recovery
5. **Multiple Destinations**: Consider using multiple backup destinations for redundancy

## Maintenance

### Logs

View service logs:
```bash
docker compose -f duplicati/docker-compose.yml logs -f duplicati
```

### Updates

Update to the latest version:
```bash
docker compose -f duplicati/docker-compose.yml pull
docker compose -f duplicati/docker-compose.yml up -d
```

### Backup Configuration

Export your Duplicati configuration from the web interface and store it securely.

## Troubleshooting

### Common Issues

1. **Permission Errors**:
   - Ensure `PUID` and `PGID` match your system user
   - Check source path permissions

2. **Cannot Access Web Interface**:
   - Verify Traefik is running and configured
   - Check DNS resolution for your hostname
   - Confirm firewall settings

3. **Backup Failures**:
   - Check available disk space
   - Verify destination credentials
   - Review backup job logs in the web interface

4. **Performance Issues**:
   - Adjust backup timing to avoid peak usage
   - Consider excluding large temporary files
   - Monitor system resources during backups

### Log Analysis

Monitor backup operations:
```bash
# Container logs
docker logs stacksmith_duplicati

# Duplicati specific logs are available in the web interface
# Go to About → Show log → Live
```

## Security Considerations

- **Web Interface Password**: Always set `DUPLICATI_WEBSERVICE_PASSWORD`
- **Encryption**: Use strong encryption passwords for backup jobs
- **Network Access**: Service is only accessible via Tailscale VPN through Traefik
- **Source Data**: Mounted read-only to prevent accidental modification
- **Regular Updates**: Keep the container image updated for security patches

## Integration with Stacksmith

This service integrates seamlessly with the Stacksmith infrastructure:

- **Traefik Integration**: Automatic SSL certificates and routing
- **Network Isolation**: Communicates through the dedicated `stacksmith` network
- **Consistent Naming**: Follows `stacksmith_servicename` convention
- **Standard Configuration**: Uses common environment variables (PUID, PGID, TZ)

## Backup Strategies

### Home Lab Backup

```bash
# Backup user data, configurations, and media
DUPLICATI_SOURCE_PATH=/home/user:/mnt/media:/etc/docker
```

### Docker Container Backup

```bash
# Backup Docker volumes and configurations
DUPLICATI_SOURCE_PATH=/var/lib/docker/volumes:/opt/docker-compose
```

### Development Workspace

```bash
# Backup development projects and configurations
DUPLICATI_SOURCE_PATH=/home/user/projects:/home/user/.config
```

## Related Services

- **Traefik**: Provides SSL termination and reverse proxy
- **Portainer**: Docker container management
- **Pi-hole**: DNS service that can be backed up
- ***arr Stack**: Media management services that can be backed up

For more information about Duplicati, visit the [official documentation](https://duplicati.readthedocs.io/).