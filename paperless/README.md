# Paperless-ngx

Private document intake, OCR and retrieval with Paperless-ngx **3.1.3**, PostgreSQL **17.11** and Redis **8.2.9**. Release tags are pinned in Compose; review upgrades explicitly. No AI, calendar integration, archive migration, Tika/Gotenberg, scanner server or backup scheduler is included.

## Prerequisites and boundaries

- Docker Compose with long-form bind mounts and health-based dependencies; Portainer Docker Standalone stacks are supported, not Swarm.
- Existing external `stacksmith` network and Stacksmith Traefik, including `websecure-tailscale`, the `stacksmith` certificate resolver and `secure-headers@docker`.
- DNS for `PAPERLESS_HOSTNAME` pointing to the host's Tailscale address. The Traefik entrypoint must actually bind only to that address; labels alone are not a firewall. Permit intended users in your tailnet policy.
- Local-disk Docker volumes, particularly PostgreSQL. Do not put its data directory on SMB/NFS. Intake/export bind directories may be backed by separately managed storage.

Only Paperless joins the shared proxy network. PostgreSQL and Redis use an internal backend network; none of the services publish host ports. Paperless login remains required. Host administrators and containers with access to the shared proxy network are part of the trust boundary; stored documents are not encrypted by this stack.

## Setup

From this directory:

```bash
cp .env.example .env
chmod 600 .env
```

Edit `.env`: set the hostname, generate **different** random values for `PAPERLESS_SECRET_KEY` and `PAPERLESS_DB_PASSWORD`, and choose absolute intake/export paths plus a host UID/GID. Empty secrets deliberately fail Compose validation. Keep the signing key stable and store recovery secrets in a password manager. Do not commit `.env` or include rendered Compose output in public logs.

Create dedicated directories on the **Docker host**, not merely the Portainer server. For the example paths and UID/GID:

```bash
sudo install -d -m 0750 -o 1000 -g 1000 /srv/paperless/consume /srv/paperless/export
docker compose --env-file .env config --quiet
docker compose --env-file .env pull
docker compose --env-file .env up -d
docker compose --env-file .env ps
```

The long-form mounts refuse missing host directories instead of silently creating them. Paperless maps its application user to `PAPERLESS_UID`/`PAPERLESS_GID`; make sure storage permissions allow that user to read, write and remove intake files and write exports. Do not mount an existing archive as intake: successfully consumed files are removed from the drop directory.

For Portainer Git deployment, use repository path `paperless/docker-compose.yml` and supply the variables from `.env.example` in Portainer's stack environment. No build step or repository-relative host bind paths are needed. Never paste the production environment into the public repository.

### First login and review inbox

Create an administrator interactively (no persistent bootstrap password in Compose):

```bash
docker compose --env-file .env exec paperless python manage.py createsuperuser
```

In Portainer, use its interactive container console and run `python manage.py createsuperuser` from `/usr/src/paperless/src`.

1. Open `https://<PAPERLESS_HOSTNAME>` and sign in. Create separate non-superuser accounts for other users; grant document permissions deliberately.
2. Create an **Inbox** tag and enable its **Inbox tag** flag before uploading documents. This is one-time application state, not Compose-managed configuration. Inbox tags are automatically assigned to new documents. Recreating empty volumes requires setup again; an export/restore preserves application state.
3. Start with browser uploads and a disposable, non-sensitive multipage scan. Check every page, OCR text, original download, document date and Inbox assignment. Remove Inbox only after reviewing completeness, metadata and any required action.
4. Verify another user's access and HTTPS login/logout before real intake. Check that a non-tailnet client cannot reach the service.

German + English OCR and `Europe/Zurich` are configured. OCR mode `skip` retains existing PDF text layers rather than redoing them; image-only scans are OCRed. Paperless retains original documents alongside derived archive files. Date/classification suggestions still need review; no filenames, taxonomy or deadline automation are imposed.

### Later scanner intake

Paperless is not an SMB/SFTP server. Connect a separately managed scanner drop folder to `PAPERLESS_CONSUME_DIR` later. A scanner writer needs suitable group/ACL permissions without access to media, database or exports. Prefer completed-file/atomic delivery. For SMB/NFS intake, set `PAPERLESS_CONSUMER_POLLING=10` (seconds) because filesystem notifications may not propagate; test slow multipage transfers before trusting it. Keep the database local regardless of intake location.

## Storage and health

| Storage | Contents |
| --- | --- |
| `stacksmith_paperless_data` | Search/index and auxiliary application data |
| `stacksmith_paperless_media` | Originals, archive PDFs and thumbnails |
| `stacksmith_paperless_db` | PostgreSQL database: users, metadata, permissions, workflows |
| `stacksmith_paperless_redis` | Persistent Redis queue/state (AOF enabled) |
| `PAPERLESS_CONSUME_DIR` | Pending intake; not the canonical archive |
| `PAPERLESS_EXPORT_DIR` | Native exports; sensitive recovery material |

Container names and volume names are fixed for one instance per host. A different Compose project name alone does **not** isolate a second installation; restore drills need a separate Docker host/daemon or an explicit override of all names, routes and bind paths.

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs --since 10m paperless paperless-db paperless-redis
docker compose --env-file .env exec -T paperless document_sanity_checker
```

Health checks cover HTTP responsiveness, PostgreSQL readiness and Redis ping; they do not prove OCR, login, permissions, backup success or restoration. Initial migrations/OCR startup may take longer than an ordinary restart.

## Backup and restore

**An export directory is not a backup strategy. Do not make this the sole archive until scheduled independent copies, failure alerts and a successful isolated restore test exist.** This stack does not install those facilities.

### Export

Pause scanner deliveries/uploads and other mutations, and let consumption finish before exporting. Use a fresh timestamped directory so failed or older exports are not mistaken for the current one:

```bash
BACKUP_DIR="../export/backup-$(date -u +%Y%m%dT%H%M%SZ)"
docker compose --env-file .env exec -T --user paperless paperless mkdir "$BACKUP_DIR" && \
  docker compose --env-file .env exec -T --user paperless paperless document_exporter "$BACKUP_DIR"
```

Check the command's exit status and export contents. The native export contains original/archive documents, thumbnails, metadata and database contents. **API tokens are excluded** and must be regenerated after restoration. Protect exports as highly sensitive, including account data.

Copy successful exports with an external, scheduled backup tool to encrypted, versioned storage on an independent device **and** an independent off-site destination. Retain older successful generations; alert on failed/stale exports and failed copies. Also protect the Compose files/version pins, deployment environment and signing key, recovery credentials and any not-yet-consumed intake. A readable one-way PDF export or sync is not a substitute for the full recovery export. Never treat a tar of a running PostgreSQL volume as a consistent database backup.

### Isolated restore drill / recovery

1. Retrieve a completed export and its deployment configuration. Use the **same Paperless version** as the export first; upgrade only after recovery succeeds.
2. On an isolated Docker host/daemon, prepare fresh empty named volumes and intake/export directories. Use a test hostname, no scanner connections and no production routes. Copy the chosen backup folder into its export directory, readable by the mapped UID/GID. Do not reuse production volumes or create users/tags before import.
3. Configure recovery secrets, start the stack and wait for initial migrations and healthy services. On this otherwise empty instance, run (replace the directory name with the actual backup):

   ```bash
   docker compose --env-file .env exec -T paperless document_importer ../export/backup-TIMESTAMP
   docker compose --env-file .env restart paperless
   docker compose --env-file .env exec -T paperless document_sanity_checker
   ```

4. Sign in using a restored account. Verify document counts, representative original downloads and checksums, archive PDFs, OCR search, dates, tags, user permissions and Inbox behavior. Regenerate API tokens and check any integrations separately.
5. Record the recovered version, backup generation and results before declaring recovery usable. Remove only the isolated test resources afterward; never run `down -v` against the live archive.

### Upgrades

Read upstream release/migration notes; export and independently copy a recovery generation **before** changing pins. Record the old Compose version and keep its secrets. Pull the reviewed images, redeploy, inspect logs/health, then test login, ingest, OCR, search and export. PostgreSQL major upgrades require an explicit supported migration, not simply changing its tag. Changing `PAPERLESS_DB_PASSWORD` on an initialized volume does not rotate the database role password automatically.

If an upgrade migrates the schema, do not assume downgrading the image will undo it: restore the pre-upgrade export into fresh storage at its matching Paperless version, leaving the failed instance intact until recovery is verified.

## Upstream references

- [Paperless-ngx installation](https://docs.paperless-ngx.com/setup/)
- [Configuration for the pinned release](https://github.com/paperless-ngx/paperless-ngx/blob/v3.1.3/docs/configuration.md)
- [Recommended workflow and inbox](https://github.com/paperless-ngx/paperless-ngx/blob/v3.1.3/docs/usage.md#usage-recommended-workflow)
- [Exporter, importer and backup caveats](https://github.com/paperless-ngx/paperless-ngx/blob/v3.1.3/docs/administration.md)
