# Home Assistant Core Service

Smart home automation platform with web-based device integration.

## Prerequisites
- Traefik reverse proxy
- IoT devices (Hue Bridge, WiFi devices, etc.)
- Tailscale VPN access

## Configuration

```bash
cp homeassistant/.env.example homeassistant/.env
# Edit with your hostname
```

**Pre-configured for Traefik**: Reverse proxy settings included, standard onboarding preserved.

## Deployment

```bash
docker compose -f traefik/docker-compose.yml -f homeassistant/docker-compose.yml up -d
```

## Setup

1. Access web interface at your configured hostname
2. Create admin account and set location
3. Add integrations (Hue Bridge, WiFi devices, etc.)
4. Create automations and dashboards

## Popular Integrations

- **Philips Hue, LIFX**: Smart lighting
- **Nest, Ecobee**: Thermostats
- **TP-Link Kasa, Shelly**: Smart switches
- **Voice Assistants**: Google, Alexa
- **Weather, notifications, cloud storage**

Built-in authentication with Tailscale VPN access. SSL via Traefik. Configuration persisted in Docker volumes.