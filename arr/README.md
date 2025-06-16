# *arr Media Management Suite

This stack provides a complete media management solution with the following services:

- **Sonarr**: TV series management and monitoring
- **Radarr**: Movie collection management and monitoring  
- **Prowlarr**: Indexer management for both Sonarr and Radarr
- **qBittorrent**: BitTorrent client for downloading content
- **Recyclarr**: Automated quality profile and custom format management
- **qbit_manage**: Automated cleanup of completed downloads

## Prerequisites

1. **JumpCloud OAuth**: The JumpCloud authentication service must be running
2. **Traefik**: The reverse proxy must be configured and running
3. **Storage**: Either local directories or NFS shares for media storage

## Configuration

### Environment Variables

Copy `arr/.env.example` to `arr/.env` and configure:

```bash
# *arr Service Hostnames
SONARR_HOSTNAME=pvrs.example.com
RADARR_HOSTNAME=pvrm.example.com
PROWLARR_HOSTNAME=pvri.example.com
QBITTORRENT_HOSTNAME=down.example.com

# Downloads Directory
DOWNLOADS_PATH=./downloads

# Media Directories
PVRS_PATH=/mnt/media/series
PVRM_PATH=/mnt/media/movies

# User/Group IDs (match your system user)
PUID=1000
PGID=1000

# Timezone
TZ=Europe/Zurich

# qBittorrent Configuration
TORRENT_PORT=6881
```

### NFS Mount Setup (Optional)

Mount NFS shares on the Docker host before starting services:

```bash
# Create mount points
sudo mkdir -p /mnt/media

# Mount NFS shares (add to /etc/fstab for persistence)
sudo mount -t nfs ${NFS_SERVER}:${NFS_SHARE} /mnt/media
```

The containers then use simple bind mounts:
- TV series: Host `${PVRS_PATH}` → Container `/series`
- Movies: Host `${PVRM_PATH}` → Container `/movies`
- Downloads: Configurable local directory → Container `/downloads`

## Deployment

```bash
docker compose up -d
```

## Initial Setup

1. **Prowlarr** (pvri.example.com):
   - Configure indexers/trackers
   - Add applications: Sonarr (http://sonarr:8989) and Radarr (http://radarr:7878)
   - Get API keys from Sonarr/Radarr (Settings → General → API Key)

2. **Sonarr** (pvrs.example.com):
   - Add root folder: `/series`
   - Configure download client (qBittorrent)
   - Add indexers from Prowlarr

3. **Radarr** (pvrm.example.com):
   - Add root folder: `/movies`
   - Configure download client (qBittorrent)
   - Add indexers from Prowlarr

4. **qBittorrent** (down.example.com):
   - Web UI protected by JumpCloud OAuth for external access
   - API only accessible from within Docker network (secure)
   - No password required for web access
   - Configure download client in Sonarr/Radarr: `http://qbittorrent:8080`
   - Downloads directory is configured via `DOWNLOADS_PATH` environment variable
   - Create subdirectories `/downloads/incomplete` and `/downloads/complete` as needed
   - Configure categories for Sonarr/Radarr

5. **Recyclarr**:
   - Configure via web interface or config files in the container
   - Add Sonarr/Radarr instances with their API keys
   - Sync TRaSH guide quality profiles and custom formats
   - Automate quality management across your *arr stack

6. **qbit_manage**:
   - Automatically cleans up completed downloads at 1.0 ratio
   - Default config provided in `qbit-manage-config.yml`
   - Removes orphaned, unregistered, and broken torrents
   - Handles what Sonarr/Radarr built-in cleanup often fails to do

## Security

All web interfaces are protected by JumpCloud OAuth authentication via Traefik middleware.

## File Structure

```
arr/
├── docker-compose.yml
├── .env.example
└── qbit-manage-config.yml
```

Configuration data is stored in Docker volumes for persistence. Download directories will be created automatically based on your `DOWNLOADS_PATH` configuration.