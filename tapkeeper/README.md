# Tapkeeper

Single-owner Telegram watch-wear logging with SQLite and outbound long polling.
[Source and image build](https://github.com/MichaelSchmidle/tapkeeper) ·
[Runtime/configuration](https://github.com/MichaelSchmidle/tapkeeper/blob/main/docs/RUNTIME.md)

No incoming ports, Traefik labels, or shared `stacksmith` network are needed.
Deploy this subfolder independently in Portainer or Docker Compose. The image must
be prebuilt; Portainer does not build it. Initial image workflow targets linux/amd64.

## Image and rolling updates

Compose uses `ghcr.io/michaelschmidle/tapkeeper:latest` directly; no image environment
variable is required. Passing main-branch builds publish `latest`; PR builds do not.
Version tags remain available and do not move `latest`. Verify registry access with
`docker compose pull` before deployment.

This follows Stacksmith's rolling-update policy, accepting occasional breaking updates
instead of routine version-bump maintenance. Configure automatic pull/redeployment in
Portainer if desired: the tag alone does not schedule updates. Keep recoverable backups
and record the actual running image identity; restoring `latest` later is not rollback.
This bundle alone is not initial deployment or migration approval.

## Setup

Copy `.env.example` to private deployment settings (Portainer stack variables work).
Set absolute **Docker-host** paths for all mounts; missing paths fail rather than
silently creating empty directories. Never put private files in this repository.

- `TAPKEEPER_CONFIG_FILE`: existing catalogue-only JSON (`{"watches":{"synthetic.reference":"Synthetic watch"}}`).
- `TAPKEEPER_TOKEN_FILE`: existing UTF-8 file containing only the dedicated bot token.
- `TAPKEEPER_DATA_DIR`: existing local-filesystem directory for SQLite and sidecars.
- `TAPKEEPER_USER_ID`: positive Telegram owner ID; also used as the private chat destination.
- `TZ`, `TAPKEEPER_MORNING`, `TAPKEEPER_EVENING`: one authoritative local schedule,
  default/examples Europe/Zurich and 10:00/20:00.

UID/GID is fixed at **10001:10001**. Prepare the data directory as that owner, mode
0700; give configuration and token that owner and mode 0400 (or equivalent restrictive
ACLs). Rootless/user-namespace Docker requires mapped ownership. Do not solve a
permission error by making secrets world-readable or the service root. Avoid SMB/NFS
for the database. Environment alone controls timezone/schedule; JSON accepts only `watches`. Old
scalar/topic JSON is rejected before database/network initialization. Only private
1:1 chats are supported: incoming sender and chat are both checked against the owner
ID; groups/topics are rejected. Old `TAPKEEPER_CHAT_ID` stack variables can be removed.

Keep the env-file private (0600), with literal `KEY=value` entries, no quotes,
expansion, duplicate keys or inline comments. Store token contents only in the token
file. The same env-file is the scalar source for deployment and offline backup; fill
all four runtime values explicitly for backup, even where Compose offers defaults.
Do not override these scalar settings in the shell. Portainer users must keep a
matching private Docker env-file for recovery and update both under the backup lock.

From this folder, with the private `.env` configured:

```sh
docker compose config --quiet
docker compose pull
# Only after explicit live-operation approval; exactly one poller per token/database:
docker compose up -d
docker compose ps
docker compose logs --since 5m tapkeeper
```

Container restart supervision does not prove working polling/scheduling. Logs are
bounded; upstream redacts operational failures. Verify a scheduled prompt and an
authorized selection/export in the intended destination after approved cutover.
Never run two instances against the same bot/database. Do not run `compose up` for
an offline rehearsal: use the following commands instead.

## Offline backup and isolated restore

Export the same config/data paths into your shell from your private deployment
settings. Set `BACKUP_IMAGE` to the exact image used by the source database, not a
freshly pulled `latest`. For an existing container, obtain its local image ID with
`docker inspect --format '{{.Image}}' stacksmith_tapkeeper`; for recovery on another
host, pull the registry digest recorded with the snapshot. Keep that image fixed
through backup/restore and coordinate with automatic redeployments. Set `B` to a
**new** backup filename, `R` to a new isolated restore directory owned by 10001:10001,
and `BACKUPS` to an existing private backup directory owned by that UID. All paths below are absolute Docker-host paths. Set `ENV_FILE` to that same private
Docker env-file. No token contents or token mount are needed.

```sh
# Online-consistent backup; may run alongside the one poller.
docker run --rm --network none --env-file "$ENV_FILE" --read-only --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --mount "type=bind,src=$TAPKEEPER_CONFIG_FILE,dst=/config.json,readonly" \
  --mount "type=bind,src=$TAPKEEPER_DATA_DIR,dst=/data" \
  --mount "type=bind,src=$BACKUPS,dst=/backups" \
  "$BACKUP_IMAGE" --config /config.json --db /data/tapkeeper.db backup "/backups/$B"

# R must be separate from live storage. Existing destination DB is refused.
docker run --rm --network none --env-file "$ENV_FILE" --read-only --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --mount "type=bind,src=$TAPKEEPER_CONFIG_FILE,dst=/config.json,readonly" \
  --mount "type=bind,src=$BACKUPS,dst=/backups,readonly" \
  --mount "type=bind,src=$R,dst=/restore" \
  "$BACKUP_IMAGE" --config /config.json --db /restore/tapkeeper.db restore "/backups/$B"

docker run --rm --network none --env-file "$ENV_FILE" --read-only \
  --mount "type=bind,src=$TAPKEEPER_CONFIG_FILE,dst=/config.json,readonly" \
  --mount "type=bind,src=$R,dst=/restore" \
  "$BACKUP_IMAGE" --config /config.json --db /restore/tapkeeper.db export /restore/check.csv
```

Compare the restored CSV against a snapshot from the same backup point, plus full
SQLite tables (prompts and replay receipts included); export alone is not full recovery.
Use matching catalogue configuration: opening a Store synchronizes that catalogue.
Preserve catalogue/env-file/token securely alongside snapshots; encrypt off-host backups. Schedule
this through the operator's existing backup system and agree retention, ownership and
recovery point/time before production. This bundle installs no backup scheduler.

## Upgrade and rollback

For a controlled update, stop the service, take a consistent backup and preserve
matching catalogue/env-file/token and the old image digest. Pull `latest` and recreate
through the same manager. Automatic updates can bypass that pre-upgrade checkpoint;
choose backup frequency accordingly and retain image identities with snapshots.
For rollback, pause automatic updates, stop the
poller, preserve all newer data, restore a compatible snapshot into a new directory and
switch the data path and image pin together. Account explicitly for writes since the
snapshot; do not delete them or assume a code downgrade undoes schema changes.

The optional upstream [backup operator](https://github.com/MichaelSchmidle/tapkeeper/blob/main/docs/BACKUPS.md)
requires `env_file` pointing to this same file. It freezes and archives the settings,
verifies catalogue/env/token immutability and runs only the native offline command.
It installs nothing here; existing operational installations remain unchanged until
separately approved and requalified with the matching image and catalogue format.
The operator uses a separately configured immutable image: a moving deployment tag
does not update that setting. Keep its image compatible with the deployed database
before enabling automated backups or accepting a schema-changing rolling update.
