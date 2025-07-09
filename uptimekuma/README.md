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

## Storage Requirements

**Important**: Requires local storage. Does **NOT** support NFS.

HTTPS via Traefik. Uses SQLite database. Data persisted in Docker volumes. Monitor your Stacksmith services and external endpoints.

