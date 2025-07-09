# Pi-hole DNS Service

DNS server with ad-blocking for upstream DNS queries. Gateway uses Pi-hole as upstream DNS server.

## Architecture
```
Clients → Gateway (DHCP + Local DNS) → Pi-hole (Ad Blocking) → Internet DNS
```

## Prerequisites
- Traefik reverse proxy
- JumpCloud OAuth (optional)
- Gateway configured to use Pi-hole as upstream

## Configuration

```bash
cp pihole/.env.example pihole/.env
# Edit with your hostname, password, and host IP
```

### Upstream DNS Options
- **Standard**: Cloudflare (1.1.1.1), Quad9 (9.9.9.9)
- **DNS-over-HTTPS**: Encrypted queries, better privacy

## Deployment

```bash
docker compose -f traefik/docker-compose.yml -f pihole/docker-compose.yml up -d
```

## Gateway Setup

1. Find Pi-hole container IP: `docker inspect pihole | grep IPAddress`
2. Configure gateway/router to use Pi-hole as upstream DNS
3. Set primary DNS to Pi-hole IP, secondary to 8.8.8.8 (fallback)

## Features

- **Web Interface**: Query logs, statistics, blocklist management
- **DNS Service**: Port 53 for gateway access
- **Protected by JumpCloud OAuth** (optional)

## Testing

```bash
# Test DNS resolution
nslookup google.com [pihole-ip]

# Test ad blocking (should be blocked)
nslookup doubleclick.net [pihole-ip]
```

Binds to specific host IP to avoid port conflicts. Blocklists update automatically. Web interface protected by JumpCloud OAuth.