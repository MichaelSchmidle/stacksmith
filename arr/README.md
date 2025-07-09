# *arr Media Management Suite

Complete media automation stack with Sonarr, Radarr, Prowlarr, qBittorrent, and automated quality management.

## Prerequisites
- Traefik reverse proxy
- Media storage (local or NFS)
- Tailscale VPN access

## Configuration

```bash
cp arr/.env.example arr/.env
# Edit with your hostnames and storage paths
```

### Storage Setup
```bash
# For NFS storage (optional)
sudo mkdir -p /mnt/media
sudo mount -t nfs ${NFS_SERVER}:${NFS_SHARE} /mnt/media
```

## Deployment

```bash
docker compose -f traefik/docker-compose.yml -f arr/docker-compose.yml up -d
```

## Setup

1. **Prowlarr**: Configure indexers and add Sonarr/Radarr apps
2. **Sonarr**: Add root folder `/series`, configure qBittorrent client
3. **Radarr**: Add root folder `/movies`, configure qBittorrent client
4. **qBittorrent**: Protected by OAuth, no password needed
5. **Recyclarr**: Auto-syncs TRaSH guide quality profiles
6. **qbit_manage**: Auto-cleanup at 1.0 ratio

All services protected by Tailscale VPN access. Configuration persisted in Docker volumes.