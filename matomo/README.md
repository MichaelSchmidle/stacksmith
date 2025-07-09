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

HTTPS via Traefik with Let's Encrypt. Data persisted in Docker volumes. Use strong database passwords.

