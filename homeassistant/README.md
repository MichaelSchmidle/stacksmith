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
| `HOMEASSISTANT_LAN_HOST` | Docker host's LAN address (IP or resolvable hostname) |

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

## Zigbee Coordinator (USB Dongle)

For Zigbee device support (Aqara, IKEA, etc.), a USB coordinator is passed through to the container.

### Host Setup

1. **Identify the dongle:**
```bash
   ls -la /dev/ttyUSB* /dev/ttyACM*
   udevadm info -a -n /dev/ttyUSB0 | grep -E 'idVendor|idProduct|serial'
```

2. **Create stable symlink** (`/etc/udev/rules.d/99-zigbee.rules`):
```
   SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", ATTRS{serial}=="YOUR_SERIAL", SYMLINK+="zigbee"
```

3. **Reload udev:**
```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ls -la /dev/zigbee  # verify symlink
```

### Container Config

Add to `homeassistant` service in `docker-compose.yml`:
```yaml
    devices:
      - /dev/zigbee:/dev/zigbee
```

### Home Assistant

Add the **ZHA** (Zigbee Home Automation) integration, pointing to `/dev/zigbee`.

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