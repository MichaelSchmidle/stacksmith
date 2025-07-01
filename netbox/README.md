# Netbox Network Documentation

Netbox is a web-based application designed to help manage and document computer networks. This stack provides a complete Netbox deployment with PostgreSQL database and Redis cache.

## Services

- **Netbox**: Network documentation and IP address management (IPAM)
- **PostgreSQL**: Primary database for Netbox
- **Redis**: Cache and session storage

## Prerequisites

1. **Traefik**: The reverse proxy must be configured and running
2. **External Network**: The `stacksmith` Docker network must exist

## Configuration

### Environment Variables

Copy `netbox/.env.example` to `netbox/.env` and configure:

```bash
# Netbox Network Documentation Hostname
NETBOX_HOSTNAME=ipam.example.com

# Netbox Admin User Configuration
NETBOX_SUPERUSER_EMAIL=admin@example.com
NETBOX_SUPERUSER_PASSWORD=changeme123

# Netbox Secret Key (generate a random 50+ character string)
NETBOX_SECRET_KEY=your-very-long-random-secret-key-here-minimum-50-characters

# Database Configuration
NETBOX_DB_NAME=netbox
NETBOX_DB_USER=netbox
NETBOX_DB_PASSWORD=netbox_password_changeme

# Redis Configuration
NETBOX_REDIS_PASSWORD=redis_password_changeme

# User/Group IDs (match your system user)
PUID=1000
PGID=1000

# Timezone
TZ=Europe/Zurich
```

### Security Configuration

**IMPORTANT**: Before deploying to production:

1. **Generate a secure secret key**: The `NETBOX_SECRET_KEY` must be at least 50 characters long and cryptographically secure
2. **Change default passwords**: Update all database and admin passwords
3. **Use strong passwords**: Ensure all passwords meet security requirements

You can generate a secure secret key using:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(60))"
```

## Deployment

```bash
# Navigate to the stacksmith directory
cd /path/to/stacksmith

# Deploy Netbox stack
docker compose -f netbox/docker-compose.yml up -d
```

## Initial Setup

1. Access Netbox at your configured hostname (e.g., https://ipam.example.com)
2. Log in with the superuser credentials from your `.env` file
3. Complete the initial setup wizard
4. Configure your network documentation structure

### Basic Configuration Steps

1. **Sites**: Create locations where your network equipment is housed
2. **Device Types**: Define models of network devices you manage
3. **Device Roles**: Create roles like "Core Switch", "Access Point", etc.
4. **IP Addresses**: Document your IP address space and assignments
5. **VLANs**: Track VLAN configurations across your network
6. **Cables**: Document physical connections between devices

## Data Persistence

All data is stored in Docker volumes:
- `netbox-db-data`: PostgreSQL database files
- `netbox-redis-data`: Redis cache and session data
- `netbox-config`: Netbox application configuration

## Backup

### Database Backup
```bash
# Create database backup
docker exec stacksmith_netbox_db pg_dump -U netbox netbox > netbox_backup.sql

# Restore database backup
docker exec -i stacksmith_netbox_db psql -U netbox netbox < netbox_backup.sql
```

### Volume Backup
```bash
# Backup all Netbox volumes
docker run --rm -v netbox-db-data:/data -v netbox-redis-data:/redis -v netbox-config:/config -v $(pwd):/backup alpine tar czf /backup/netbox_volumes_backup.tar.gz /data /redis /config
```

## Troubleshooting

### Container Won't Start
- Check that PostgreSQL is healthy before Netbox starts
- Verify all environment variables are set correctly
- Check Docker logs: `docker compose logs netbox`

### Database Connection Issues
- Ensure database credentials match between services
- Verify the database container is running: `docker compose ps`
- Check network connectivity between containers

### Secret Key Issues
- The secret key must be consistent across restarts
- Generate a new key only for fresh installations
- Never change the secret key after initial setup

## Security

- All web interfaces are accessible through Traefik with automatic HTTPS
- Database and Redis are only accessible within the Docker network
- Admin authentication is handled by Netbox's built-in user system
- Consider integrating with external authentication providers for enterprise use

## File Structure

```
netbox/
├── docker-compose.yml
├── .env.example
└── README.md
```

Configuration data is stored in Docker volumes for persistence. The Netbox application will initialize its database schema automatically on first startup.