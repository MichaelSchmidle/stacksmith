# Pi-hole DNS Service

Pi-hole DNS server configured as upstream DNS for gateways. Provides ad-blocking and DNS filtering while maintaining local hostname resolution through your network gateway.

## Service Overview

- **Image**: `pihole/pihole:latest`
- **Purpose**: DNS server with ad-blocking for upstream DNS queries
- **Ports**: 53 (DNS), 8080 (Web interface via Traefik)
- **Network**: Traefik network for web interface
- **DHCP**: Disabled (gateway handles DHCP)

## Architecture

```
Clients → Gateway (DHCP + Local DNS) → Pi-hole (Ad Blocking) → Internet DNS
```

## Dependencies

**Required Services**:
- **Traefik**: Provides reverse proxy for Pi-hole web interface

**Optional Services**:
- **JumpCloud Auth**: Provides authentication for Pi-hole web interface

**External Dependencies**:
- **Gateway**: Configured to use Pi-hole as upstream DNS server

## Configuration

### Environment Variables

Copy and configure the environment file:
```bash
cp .env.example .env
```

**Required Variables**:
- `PIHOLE_HOSTNAME`: Hostname for Pi-hole web interface (e.g., `dns.example.com`)
- `PIHOLE_PASSWORD`: Admin password for Pi-hole web interface

**Optional Variables**:
- `PIHOLE_WEB_PORT`: Internal web server port (default: `8080`)
- `PIHOLE_DNS_PORT`: DNS server port (default: `53`)
- `PIHOLE_DNS_UPSTREAMS`: Upstream DNS servers Pi-hole forwards to (default: Google/Cloudflare DNS)
- `TZ`: Timezone (default: `UTC`)

### Upstream DNS Configuration

Configure which DNS servers Pi-hole forwards to:

#### Standard DNS (Fast)
```bash
# Cloudflare + Quad9 (recommended)
PIHOLE_DNS_UPSTREAMS=1.1.1.1;1.0.0.1;9.9.9.9;149.112.112.112

# Cloudflare only
PIHOLE_DNS_UPSTREAMS=1.1.1.1;1.0.0.1

# Quad9 only (privacy-focused)
PIHOLE_DNS_UPSTREAMS=9.9.9.9;149.112.112.112
```

#### DNS-over-HTTPS (Secure/Private)
```bash
# Cloudflare + Quad9 DoH
PIHOLE_DNS_UPSTREAMS=https://1.1.1.1/dns-query;https://1.0.0.1/dns-query;https://dns.quad9.net/dns-query

# Cloudflare DoH only
PIHOLE_DNS_UPSTREAMS=https://1.1.1.1/dns-query;https://1.0.0.1/dns-query

# AdGuard DoH (additional filtering)
PIHOLE_DNS_UPSTREAMS=https://dns.adguard.com/dns-query
```

**DoH vs Standard DNS:**
- **Standard DNS**: Faster, less overhead, easier to troubleshoot
- **DNS-over-HTTPS**: Encrypted queries, better privacy, slightly slower

## Deployment

### Standalone Deployment
```bash
# Configure environment
cp .env.example .env
# Edit .env with your settings

# Deploy Pi-hole with Traefik
docker compose -f ../traefik/docker-compose.yml -f docker-compose.yml up -d
```

### With Authentication
```bash
# Deploy Pi-hole with Traefik and JumpCloud auth
docker compose -f ../traefik/docker-compose.yml -f ../jumpcloud/docker-compose.yml -f docker-compose.yml up -d
```

### With Full Stack
```bash
# Deploy complete stack
docker compose -f ../docker-compose.yml -f ../traefik/docker-compose.yml -f ../jumpcloud/docker-compose.yml -f docker-compose.yml up -d
```

## Gateway Configuration

### Find Pi-hole Container IP
```bash
# Get Pi-hole container IP address
docker inspect pihole | grep "IPAddress"

# Alternative: Check network configuration
docker network inspect stacksmith | grep -A 5 pihole
```

### Configure Gateway DNS Settings

Configure your network gateway/router to use Pi-hole as upstream DNS server:

#### Method 1: WAN/Internet DNS Configuration
1. **Access your router/gateway admin interface**
2. **Navigate to WAN/Internet settings**
3. **Set Custom DNS servers**:
   - **Primary DNS**: `[Pi-hole Container IP]` (e.g., `172.18.0.3`)
   - **Secondary DNS**: `8.8.8.8` (fallback)
4. **Apply changes and restart if required**

#### Method 2: DHCP DNS Override
1. **Navigate to DHCP/LAN settings**
2. **Configure DNS servers for DHCP clients**:
   - **Primary DNS**: `[Pi-hole Container IP]`
   - **Secondary DNS**: `8.8.8.8` (fallback)
3. **Apply to all network segments/VLANs as needed**

#### Method 3: Per-VLAN Configuration
For multi-VLAN environments:
1. **Configure each VLAN separately**
2. **Set DHCP DNS option** pointing to Pi-hole
3. **Maintain gateway as DHCP server** for each VLAN
4. **Pi-hole serves as upstream DNS** for external queries only

### Gateway-Specific Examples

**Common Router Interfaces**:
- **pfSense**: System → General Setup → DNS Servers
- **OPNsense**: System → Settings → General → DNS Servers  
- **UniFi**: Settings → Internet → WAN Networks → DNS Server
- **ASUS**: WAN → Internet Connection → DNS Server
- **Netgear**: Internet → Internet Setup → DNS Addresses

## Accessing Services

### Pi-hole Web Interface
- **URL**: `https://dns.example.com` (or your configured hostname)
- **Authentication**: JumpCloud OAuth (if enabled)
- **Features**: 
  - Query logs and statistics
  - Blocklist management
  - DNS configuration
  - Network diagnostics

### DNS Service
- **Port**: 53 (TCP/UDP)
- **Access**: Direct from network gateway
- **Protocol**: Standard DNS queries

## Testing and Validation

### Verify Pi-hole DNS Resolution
```bash
# Test DNS resolution from Pi-hole container
docker exec pihole nslookup google.com 127.0.0.1

# Test from host system (replace with Pi-hole container IP)
nslookup google.com 172.18.0.3
```

### Verify Ad Blocking
```bash
# This should be blocked by Pi-hole
nslookup doubleclick.net [pihole-ip]

# This should resolve normally
nslookup google.com [pihole-ip]
```

### Test Local Hostname Resolution
1. **From client device**: Ping local hostnames
2. **Should resolve**: Via network gateway (not Pi-hole)
3. **External domains**: Should show in Pi-hole query logs

### Check Pi-hole Query Logs
1. **Access web interface**: `https://dns.example.com`
2. **Navigate to Query Log**
3. **Verify queries**: From gateway IP are being processed

## Monitoring

### Pi-hole Statistics
- **Total queries**: Monitor DNS query volume
- **Queries blocked**: Ad-blocking effectiveness
- **Top blocked domains**: Most common blocked requests
- **Query types**: A, AAAA, PTR, etc.

### Container Health
```bash
# Monitor Pi-hole container logs
docker compose logs -f pihole

# Check container status
docker compose ps pihole

# View resource usage
docker stats pihole
```

### Network Monitoring
```bash
# Test DNS port accessibility
nc -zv [pihole-ip] 53

# Monitor DNS query traffic
docker compose exec pihole tail -f /var/log/pihole.log
```

## Troubleshooting

### Common Issues

**Ad Blocking Not Working**:
```bash
# Check Pi-hole blocklists
docker compose exec pihole pihole -g

# Update blocklists
docker compose exec pihole pihole updateGravity

# Verify DNS queries reaching Pi-hole
docker compose logs pihole | grep "query"
```

**Web Interface Issues**:
```bash
# Check Traefik routing
docker compose logs traefik | grep pihole

# Verify JumpCloud authentication
docker compose logs jumpcloud-auth
```

### Debug Commands

```bash
# Check Pi-hole container logs
docker compose logs -f pihole

# Test DNS resolution
dig @[pihole-ip] google.com
dig @[pihole-ip] doubleclick.net

# Check blocklist status
docker compose exec pihole pihole status

# View Pi-hole configuration
docker compose exec pihole cat /etc/pihole/setupVars.conf
```

### Performance Optimization

**DNS Query Performance**:
- Monitor query response times in Pi-hole logs
- Optimize upstream DNS server selection
- Consider local DNS caching on gateway

**Container Resources**:
```bash
# Monitor resource usage
docker stats pihole

# Adjust container resources if needed
docker update --memory=512m pihole
```

## Maintenance

### Blocklist Updates
```bash
# Update blocklists manually
docker compose exec pihole pihole updateGravity

# Check blocklist status
docker compose exec pihole pihole -g -l
```

### Backup Configuration
```bash
# Backup Pi-hole configuration
docker compose exec pihole pihole -a -t

# Backup volumes
docker run --rm -v pihole_pihole-config:/data -v $(pwd):/backup alpine tar czf /backup/pihole-config-backup.tar.gz /data
```

### Log Rotation
Pi-hole automatically manages log rotation, but you can manually clear logs:
```bash
# Clear query logs
docker compose exec pihole pihole flush

# Clear specific log files
docker compose exec pihole truncate -s 0 /var/log/pihole.log
```

## Security Considerations

- **Admin Password**: Use strong password for Pi-hole admin interface
- **Network Access**: DNS port 53 accessible from network gateway only
- **Web Interface**: Protected by JumpCloud authentication
- **Container Isolation**: Runs in isolated Docker network
- **Query Logging**: Monitor for unusual DNS patterns