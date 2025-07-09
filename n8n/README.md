# n8n - Workflow Automation Platform

Visual workflow automation with 400+ integrations. Self-hosted alternative to Zapier.

## Prerequisites
- Traefik reverse proxy
- Tailscale VPN access

## Configuration

```bash
cp n8n/.env.example n8n/.env
# Edit with your hostname
```

## Deployment

```bash
docker compose -f traefik/docker-compose.yml -f n8n/docker-compose.yml up -d
```

## Setup

1. Access web interface (Tailscale VPN required)
2. Create owner account
3. Build workflows with drag-and-drop editor
4. Connect services with 400+ integrations

## Use Cases

- **Home automation**: IoT devices, notifications, monitoring
- **Business**: Data sync, lead processing, reporting
- **Personal**: Email filtering, calendar sync, file management

Tailscale VPN access required. HTTPS via Traefik. Data persisted in Docker volumes. Export/import workflows via web interface.