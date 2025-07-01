# Home Assistant Core Service

Home Assistant Core configured for smart home automation with web-based IoT device integration. Provides centralized control, automation, and monitoring of connected devices through Traefik with SSL termination.

## Service Overview

- **Image**: `lscr.io/linuxserver/homeassistant:latest` (LinuxServer.io)
- **Purpose**: Smart home automation platform with web-based device integration
- **Port**: 8123 (Web interface via Traefik)
- **Network**: External network with Traefik integration
- **Device Support**: Network-based IoT devices (Philips Hue, WiFi devices, cloud integrations)

## Architecture

```
Smart Devices → Network → Traefik → Home Assistant Core → Automation Rules → User Interface
```

## Dependencies

**Required Services**:
- **Traefik**: Provides reverse proxy, SSL termination, and authentication

**Optional Services**:
- **JumpCloud Auth**: Provides additional authentication layer

**External Dependencies**:
- **IoT Devices**: Network-accessible devices (Hue Bridge, WiFi devices, etc.)
- **Cloud Services**: Weather, notifications, voice assistants

## Configuration

### Environment Variables

Copy and configure the environment file:
```bash
cp .env.example .env
```

**Required Variables**:
- `HOMEASSISTANT_HOSTNAME`: Hostname for web interface (e.g., `ha.example.com`)

**System Variables**:
- `PUID`: User ID for file permissions (default: `1000`)
- `PGID`: Group ID for file permissions (default: `1000`)
- `TZ`: Timezone (e.g., `Europe/Zurich`)

### Home Assistant Configuration (Minimal Pre-Config)

This deployment includes minimal pre-configuration to enable Traefik integration while preserving full configurability:

**Pre-configured Elements**:
- `configuration.yaml`: **Only** reverse proxy settings for Traefik compatibility
- `default_config`: Enables Home Assistant's standard onboarding flow

**What's Automated**:
- ✅ **Reverse Proxy**: Trusts Docker network ranges (172.18-21.0.0/16)
- ✅ **HTTP Security**: X-Forwarded-For enabled for Traefik
- ✅ **Web Interface Access**: Works immediately through Traefik

**What You Configure**:
- 🔧 **Initial Setup**: Location, user account, integrations (via Home Assistant UI)
- 🔧 **Device Integration**: Add your Hue Bridge and other devices
- 🔧 **Automation**: Create automations, scenes, scripts
- 🔧 **Advanced Settings**: Database retention, logging, security policies

This approach ensures the service works with your infrastructure immediately while preserving the standard Home Assistant setup experience.

## Deployment

### Prerequisites
```bash
# Ensure the external network exists
docker network create stacksmith
```

### Standalone Deployment
```bash
# Configure environment
cp .env.example .env
# Edit .env with your settings

# Deploy Home Assistant with Traefik
docker compose -f ../traefik/docker-compose.yml -f docker-compose.yml up -d
```

### With Full Stack
```bash
# Deploy complete infrastructure stack
docker compose -f ../docker-compose.yml -f ../traefik/docker-compose.yml -f docker-compose.yml up -d
```

## Accessing Services

### Home Assistant Web Interface
- **URL**: `https://ha.example.com` (or your configured hostname)
- **SSL**: Automatic Let's Encrypt certificate via Traefik
- **Authentication**: Home Assistant built-in auth + optional JumpCloud OAuth
- **Features**:
  - Device management and configuration
  - Automation rule creation
  - Dashboard customization
  - Integration configuration
  - System monitoring and logs

### Initial Setup
1. **First Visit**: Navigate to Home Assistant web interface
2. **Create User**: Set up admin account
3. **Location**: Configure geographic location
4. **Integrations**: Add IoT device integrations
5. **Automation**: Create automation rules

## Common Integrations

### Network-Based Devices (Recommended)
- **Philips Hue**: Bridge discovery via IP address
- **LIFX**: WiFi-connected smart lights
- **Nest/Ecobee**: Cloud-connected thermostats
- **WiFi Cameras**: IP cameras and security systems
- **Smart Switches**: TP-Link Kasa, Shelly devices
- **Network Storage**: Synology, QNAP integration

### Cloud Integrations
- **Voice Assistants**: Google Assistant, Amazon Alexa
- **Weather Services**: OpenWeatherMap, AccuWeather
- **Notification Services**: Pushbullet, Telegram, email
- **Cloud Storage**: Google Drive, Dropbox integration
- **Energy Monitoring**: Utility company APIs

### Manual Integration Example (Hue Bridge)
1. **Find Bridge IP**: Check router DHCP leases or use Hue app
2. **Home Assistant**: Configuration → Integrations → Add Integration
3. **Select Philips Hue**: Enter bridge IP address manually
4. **Press Bridge Button**: Physical button press for authentication
5. **Configure Devices**: Lights and sensors auto-discovered

## Testing and Validation

### Verify Home Assistant Startup
```bash
# Monitor container logs during startup
docker compose logs -f homeassistant

# Check container health
docker compose ps homeassistant

# Verify web interface accessibility
curl -k https://ha.example.com
```

### Test Device Integration
1. **Navigate to Integrations**: Configuration → Integrations
2. **Add Integration**: Click "+" to add new integration
3. **Configure Device**: Follow integration-specific setup
4. **Test Control**: Verify device control through interface

### Verify Automation
1. **Create Test Automation**: Simple time-based automation
2. **Monitor Execution**: Check automation logs in Home Assistant
3. **Device Control**: Test manual device control through interface

## Monitoring

### Home Assistant Logs
```bash
# View container logs
docker compose logs -f homeassistant

# Monitor Home Assistant system logs
docker compose exec homeassistant tail -f /config/home-assistant.log
```

### System Health
- **Web Interface**: Configuration → System → System Health
- **Shows**: Integration status, system resources, connectivity
- **Alerts**: Warnings about missing dependencies or errors

### Container Health
```bash
# Monitor resource usage
docker stats homeassistant

# Check container status
docker compose ps homeassistant

# Inspect container configuration
docker inspect stacksmith_homeassistant
```

## Troubleshooting

### Integration Issues

**Device Not Discovered**:
1. **Check Network Connectivity**: Ensure device and Home Assistant on same network
2. **Manual Configuration**: Add devices by IP address instead of auto-discovery
3. **Firewall Rules**: Verify no blocking between device and container
4. **Device Documentation**: Check manufacturer's Home Assistant integration guide

**Hue Bridge Specific**:
```bash
# Find Hue Bridge IP
nmap -sP 192.168.1.0/24 | grep -i philips

# Test bridge connectivity
curl http://[bridge-ip]/api/

# Manual integration in Home Assistant
# Configuration → Integrations → Philips Hue → Manual IP entry
```

### SSL Certificate Issues
```bash
# Check Traefik certificate generation
docker compose logs traefik | grep homeassistant

# Verify Traefik routing
curl -H "Host: ha.example.com" http://localhost:80
```

### Performance Issues
```bash
# Monitor container resources
docker stats homeassistant

# Check Home Assistant database size
docker compose exec homeassistant du -sh /config

# Review automation complexity in Home Assistant logs
```

### Common Issues

**Can't Access Web Interface**:
1. **Check Traefik**: Ensure Traefik is running and healthy
2. **DNS Resolution**: Verify hostname resolves to Traefik IP
3. **Firewall**: Check host firewall allows traffic to Traefik
4. **Container Status**: Verify Home Assistant container is running

**Integration Failures**:
1. **Configuration → Integrations**: Review failed integrations (red icons)
2. **Check Logs**: Configuration → System → Logs
3. **Network Access**: Test connectivity to device from container
4. **Reconfigure**: Remove and re-add problematic integrations

### Debug Commands

```bash
# Check Home Assistant configuration
docker compose exec homeassistant python -m homeassistant --script check_config --config /config

# View system information
docker compose exec homeassistant cat /config/.storage/core.config

# Test network connectivity
docker compose exec homeassistant ping [device-ip]
docker compose exec homeassistant curl http://[hue-bridge-ip]/api/

# Check container network settings
docker inspect stacksmith_homeassistant | grep -A 10 NetworkSettings
```

## Maintenance

### Backup Configuration
```bash
# Backup Home Assistant configuration
docker run --rm -v homeassistant_homeassistant-config:/data -v $(pwd):/backup alpine tar czf /backup/homeassistant-config-backup.tar.gz /data

# Backup specific configuration files
docker compose exec homeassistant tar czf /config/backup.tar.gz /config/configuration.yaml /config/automations.yaml /config/scripts.yaml
```

### Updates
```bash
# Update to latest version
docker compose pull homeassistant
docker compose up -d homeassistant

# Check Home Assistant release notes before updating
# https://www.home-assistant.io/blog/
```

### Database Maintenance
```bash
# Check database size
docker compose exec homeassistant du -sh /config/home-assistant_v2.db

# Purge old data (via Home Assistant web interface)
# Configuration → System → Storage → Purge
```

### Log Management
```bash
# Clear Home Assistant logs
docker compose exec homeassistant truncate -s 0 /config/home-assistant.log

# Adjust logging level in configuration.yaml
# logger:
#   default: warning
#   logs:
#     homeassistant.core: debug
```

## Security Considerations

### Network Security
- **Traefik Protection**: All traffic goes through Traefik with SSL termination
- **No Direct Exposure**: Container not directly accessible from outside
- **VPN Access**: Access via Tailscale VPN as configured in Traefik

### Authentication
- **Built-in Auth**: Home Assistant user management
- **Multi-Factor Auth**: Enable in user profile settings
- **Trusted Networks**: Configure trusted IP ranges in Home Assistant
- **API Security**: Use long-lived access tokens for external access

### Data Privacy
- **Local Processing**: Most automation logic runs locally
- **Cloud Integrations**: Review data sharing policies for cloud services
- **HTTPS Enforcement**: All web traffic encrypted via Traefik
- **Configuration Security**: Encrypt configuration backups

## Advanced Configuration

### Custom Components
```bash
# Install HACS (Home Assistant Community Store)
# Download via Home Assistant web interface
# Configuration → Integrations → Add Integration → HACS
```

### Performance Tuning
```yaml
# In Home Assistant configuration.yaml
recorder:
  purge_keep_days: 10
  db_url: sqlite:////config/home-assistant_v2.db
  
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 172.18.0.0/16  # Docker network range
```

### Integration Examples
```yaml
# Example configuration.yaml sections
automation: !include automations.yaml
script: !include scripts.yaml
scene: !include scenes.yaml

# Sample Hue light automation
automation:
  - alias: "Evening lights"
    trigger:
      platform: sun
      event: sunset
      offset: "-00:30:00"
    action:
      service: light.turn_on
      target:
        entity_id: light.living_room_hue
      data:
        brightness_pct: 80
        color_temp: 366
```

### Useful Integrations for Your Setup
- **Philips Hue**: Your primary lighting control
- **HACS**: Community integrations and custom cards
- **Node-RED**: Visual automation builder (if you deploy n8n alternative)
- **InfluxDB + Grafana**: Long-term data storage and visualization
- **Mobile App**: iOS/Android companion app for presence detection

This Home Assistant deployment provides a solid foundation for smart home automation while maintaining simplicity and security through Traefik integration.