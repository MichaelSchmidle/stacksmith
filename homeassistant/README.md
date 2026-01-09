# Home Assistant Core Service

Smart home automation platform with web-based device integration.

## Prerequisites
- Traefik reverse proxy
- IoT devices (Hue Bridge, WiFi devices, etc.)
- Tailscale VPN access

## Configuration

```bash
cp homeassistant/.env.example homeassistant/.env
# Edit with your hostname and LAN IP
```

| Variable | Description |
|----------|-------------|
| `HOMEASSISTANT_HOSTNAME` | Public hostname for Traefik routing |
| `HOMEASSISTANT_LAN_IP` | Docker host's LAN IP (for Traefik to reach HA) |

## Network Architecture

This stack uses **host networking** for Home Assistant, enabling:
- mDNS/Bonjour discovery (Apple TV, Chromecast, etc.)
- Bidirectional communication with devices that need callbacks
- Full access to LAN broadcast traffic

Traefik proxies to Home Assistant via the host's LAN IP, preserving:
- SSL termination and certificate management
- Tailscale VPN access
- Consistent hostname routing

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