# Traefik Reverse Proxy Service

Reverse proxy with automatic HTTPS via Let's Encrypt and Cloudflare DNS challenge.

## Features
- **Automatic SSL**: Let's Encrypt certificates with DNS challenge
- **Service Discovery**: Automatic routing based on Docker labels
- **Load Balancing**: Built-in load balancing
- **Tailscale Integration**: Primary access via Tailscale VPN

## Configuration

```bash
cp traefik/.env.example traefik/.env
# Edit with your hostname, email, and Cloudflare API token
```

### Cloudflare API Token
Create token with Zone:Zone:Read and Zone:DNS:Edit permissions for your domain.

## Deployment

```bash
docker network create stacksmith
docker compose -f traefik/docker-compose.yml up -d
```

## Service Integration

Services join the `stacksmith` network and use Docker labels for automatic discovery:

```yaml
networks:
  - stacksmith
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.service-name.rule=Host(`service.example.com`)"
  - "traefik.http.routers.service-name.entrypoints=websecure"
  - "traefik.http.routers.service-name.tls.certresolver=stacksmith"
```

**Tailscale entrypoint**: Services use `websecure-tailscale` for VPN access.

## Dashboard

Access dashboard at your configured hostname. Features route monitoring, service health, and SSL certificate status.

Provides automatic service discovery, SSL termination, and authentication middleware for all Stacksmith services.

## Local Development with mkcert

For local testing, use mkcert to generate trusted local SSL certificates instead of Let's Encrypt.

### Setup

1. **Install mkcert**:
   ```bash
   # macOS
   brew install mkcert

   # Linux
   sudo apt install mkcert   # Debian/Ubuntu
   sudo pacman -S mkcert     # Arch

   # Windows
   winget install mkcert     # winget
   choco install mkcert      # Chocolatey
   scoop install mkcert      # Scoop
   ```

2. **Install local CA**:
   ```bash
   mkcert -install
   ```

3. **Generate certificates**:
   ```bash
   # Replace dev.example.com with your local test domain
   cd traefik
   mkcert "*.dev.example.com" "dev.example.com"
   ```

4. **Rename and move certificates**:
   ```bash
   # Create certs directory
   mkdir -p certs

   # Move and rename to expected format
   mv _wildcard.dev.example.com+1.pem certs/cert.pem
   mv _wildcard.dev.example.com+1-key.pem certs/key.pem
   ```

5. **Deploy or restart Traefik**:
   ```bash
   docker compose -f traefik/docker-compose.yml up -d
   ```

### How Certificate Switching Works

- **mkcert mode**: When certificates exist in `traefik/certs/`, Traefik uses them as the default certificate
- **Let's Encrypt mode**: When `traefik/certs/` is empty or doesn't exist, Traefik uses Let's Encrypt
- **To switch to Let's Encrypt**: Simply remove or rename the `traefik/certs/` directory and restart Traefik
- **To switch back to mkcert**: Place certificates back in `traefik/certs/` and restart Traefik

### Notes

- mkcert certificates are only trusted on your local machine (not on other devices)
- The `traefik/certs/` directory is git-ignored to prevent committing local certificates
- Both certificate sources are configured simultaneously; presence of files determines which is used
- Traefik will log warnings if certificates are referenced but not found (safe to ignore when using Let's Encrypt)