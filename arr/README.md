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
6. Configure native completed-download cleanup as described below.

All services protected by Tailscale VPN access. Configuration persisted in Docker volumes.

## Completed-download cleanup

Sonarr and Radarr can remove imported torrents and their download files after qBittorrent reports that seeding is complete. Failed or unimported downloads are retained. Hardlinked library files remain intact when the download path is removed.

Configure this manually after the first deployment:

1. In **Prowlarr → Settings → Apps**, set both the Sonarr and Radarr applications to **Full Sync**.
2. In each **Prowlarr indexer**, show advanced settings and set its **Seed Ratio** and **Seed Time**. For public trackers, a sensible baseline is ratio `1.0` and time `2880` minutes (48 hours); qBittorrent treats these as alternative limits, so whichever is reached first ends seeding. For private trackers, use the tracker's required ratio/time instead.
3. Run **Sync App Indexers** in Prowlarr so those limits are copied to Sonarr and Radarr.
4. In both **Sonarr → Settings → Download Clients** and **Radarr → Settings → Download Clients**, enable **Completed Download Handling** and **Remove**.
5. In **qBittorrent → Settings → BitTorrent → Seeding Limits**, leave global ratio/time limits disabled and set the limit action to **Stop torrent**. Sonarr/Radarr will remove the torrent and its files only after a successful import.

These settings persist in the existing application configuration volumes across normal stack redeployments. A deployment with fresh volumes requires this one-time setup again.