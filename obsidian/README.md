# Obsidian Web Desktop Stack

This stack runs the LinuxServer.io Obsidian container as a browser-accessible desktop app, routed through Stacksmith Traefik on the Tailscale-only HTTPS entrypoint.

Official docs:

- [LinuxServer.io Obsidian image](https://docs.linuxserver.io/images/docker-obsidian/)
- [Obsidian](https://obsidian.md/)

## What this stack assumes

- Docker runs on the host that already has the Syncthing-backed Obsidian vault.
- The host vault path is bind-mounted read/write into the container at `/config/vault`.
- The container runs as the vault-owning host UID/GID, so Obsidian, Syncthing, and local tools can all keep direct file access without permission churn.
- Access is through Traefik's `websecure-tailscale` entrypoint, not public internet.

## Mount layout

The LinuxServer image uses `/config` as the container user's home directory for application settings and files. Do **not** mount the vault root directly as `/config`; that would mix Obsidian/Selkies application state into the vault.

This stack deliberately uses two mounts:

```text
obsidian-config volume          -> /config
/home/michael/ObsidianVault     -> /config/vault
```

Open `/config/vault` inside Obsidian when the desktop starts.

## Security notes

LinuxServer warns that this container exposes a web desktop with a terminal and passwordless sudo inside the container. Treat access to this service as sensitive.

This Stacksmith service therefore expects:

- Traefik/Tailscale-only exposure.
- `CUSTOM_USER`/`PASSWORD` basic auth enabled via `.env`.
- No host port publishing.
- No `seccomp=unconfined` unless the host actually requires it for Electron compatibility.

## Quick start

1. Install Docker on the target host and create the external network if needed:

```bash
docker network create stacksmith
```

2. Copy the environment file:

```bash
cp obsidian/.env.example obsidian/.env
```

3. Edit `obsidian/.env`:

```bash
OBSIDIAN_HOSTNAME=obsidian.yourdomain.com
OBSIDIAN_PUID=1000
OBSIDIAN_PGID=1000
OBSIDIAN_VAULT_PATH=/home/michael/ObsidianVault
OBSIDIAN_CUSTOM_USER=michael
OBSIDIAN_PASSWORD=replace-with-a-real-password
```

4. Start the stack:

```bash
docker compose --env-file obsidian/.env -f obsidian/docker-compose.yml up -d
```

5. Open the UI through Traefik:

```text
https://obsidian.yourdomain.com
```

Then open the vault folder inside the web desktop at:

```text
/config/vault
```

## Validation pattern

Check that the service resolved and mounted the vault as expected:

```bash
docker compose --env-file obsidian/.env -f obsidian/docker-compose.yml config
docker exec stacksmith_obsidian id
docker exec stacksmith_obsidian test -d /config/vault
docker exec stacksmith_obsidian sh -lc 'touch /config/vault/.stacksmith-write-test && rm /config/vault/.stacksmith-write-test'
```

If the write test fails, stop the container and fix `OBSIDIAN_PUID`, `OBSIDIAN_PGID`, or host-path ownership before using the web UI.

## Operational cautions

- Avoid editing the same note simultaneously from native Obsidian and web Obsidian; Syncthing can still create conflict copies.
- Keep Syncthing as the sync mechanism for private clients; this container is only a browser access path.
- Back up the vault before first serious use through the web desktop.
