# Buzz Stack

[Buzz](https://github.com/block/buzz) is a self-hosted workspace for humans and AI agents. This stack runs the relay and device-pairing service with Postgres, Redis, and [SeaweedFS](https://github.com/seaweedfs/seaweedfs) behind Traefik.

## Prerequisites

- Docker Compose and the external `stacksmith` network
- Running Stacksmith Traefik instance and Tailscale VPN access
- Buzz Desktop for the workspace UI
- [`nak`](https://github.com/fiatjaf/nak), installed with its [official installer](https://raw.githubusercontent.com/fiatjaf/nak/master/install.sh). Ensure `~/.local/bin` is on your `PATH` and `nak --version` works before continuing.

## Configuration

Run commands from the repository root:

```bash
cp buzz/.env.example buzz/.env
```

Set `BUZZ_HOSTNAME` to your private Traefik-routed hostname and replace every `CHANGE_ME` value. Do not commit `buzz/.env`.

Generate the owner identity:

```bash
OWNER_SECRET_HEX="$(nak key generate)"
printf '%s\n' "$OWNER_SECRET_HEX" | nak encode nsec
printf '%s\n' "$OWNER_SECRET_HEX" | nak key public
unset OWNER_SECRET_HEX
```

Save the first output (`nsec1...`) in a password manager for Buzz Desktop. Put the second output, the 64-character hex public key, in `BUZZ_RELAY_OWNER_PUBKEY`.

Generate a separate relay keypair (substitute your `BUZZ_IMAGE` if overridden):

```bash
docker run --rm --entrypoint buzz-admin \
  ghcr.io/block/buzz:latest \
  generate-key
```

Put its hex secret key in `BUZZ_RELAY_PRIVATE_KEY`. Keep owner and relay identities separate.

Generate a distinct value for each remaining secret with a password manager or:

```bash
openssl rand -hex 32
```

These fill `BUZZ_GIT_HOOK_HMAC_SECRET`, `BUZZ_POSTGRES_PASSWORD`, `BUZZ_REDIS_PASSWORD`, `BUZZ_S3_ACCESS_KEY`, and `BUZZ_S3_SECRET_KEY`.

## Deployment

**Existing MinIO installations: do not run these commands as an upgrade.** The new store starts empty; complete the separately planned migration below first. Disable automatic Git redeployment until cutover is approved.

For a fresh installation:

```bash
docker compose --env-file buzz/.env -f buzz/docker-compose.yml config
docker compose --env-file buzz/.env -f buzz/docker-compose.yml up -d --pull always
docker compose --env-file buzz/.env -f buzz/docker-compose.yml ps
```

## Setup

1. In Buzz Desktop, select **Use an existing key** and import the owner's saved `nsec`.
2. Connect to `wss://<BUZZ_HOSTNAME>`. The configured owner is enrolled automatically.
3. Add each additional user or agent with their own public key:

```bash
docker compose --env-file buzz/.env -f buzz/docker-compose.yml exec buzz-relay \
  buzz-admin add-member --pubkey 'NPUB_OR_HEX_PUBKEY' --role member

docker compose --env-file buzz/.env -f buzz/docker-compose.yml exec buzz-relay \
  buzz-admin list-members
```

The HTTPS hostname serves invite pages; the workspace UI is in Buzz Desktop. Mobile pairing uses the same hostname at `/pair`. For Hermes agents, see the [Buzz integration guide](https://hermes-agent.nousresearch.com/docs/integrations/buzz).

## Object storage and initialization

`buzz-seaweedfs` runs the upstream `mini` all-in-one mode (master, volume server, filer and S3 gateway). This is a single-node store, not a highly available cluster. It uses the existing `BUZZ_S3_ACCESS_KEY`, `BUZZ_S3_SECRET_KEY` and `BUZZ_S3_BUCKET` inputs; `mini` creates the bucket and initializes its administrative S3 identity natively. There is no separate client/init image or generated credential file. Empty credentials fail Compose interpolation. Changing environment variables alone is not a supported rotation procedure when persisted IAM identities already exist; plan and verify credential changes separately.

- Buzz uses path-style S3 at `http://buzz-seaweedfs:8333`.
- The whole `/data` tree persists in **`stacksmith_buzz_seaweedfs_data`**, including master state, object-volume files and filer metadata (`/data/filerldb2`). Retaining only object-volume files is not a usable backup.
- S3 credentials are required. No anonymous bucket access is configured. Storage joins only the internal network; none of its ports have host mappings or Traefik routes. Administrative/other internal listeners are not a security boundary against a compromised peer container.
- WebDAV, the admin UI, Iceberg, Lance and master telemetry are disabled. Recursive deletion of non-empty buckets and upload-driven auto-creation of buckets are disabled; the configured bucket is created explicitly at startup.
- The store health check uses its S3 `/healthz`. Buzz still performs its unchanged conditional-write conformance probe before serving Git. Keep `BUZZ_GIT_CONFORMANCE_PROBE=true`; never bypass it to admit a failing store. The relay health check allows a 180-second startup grace plus its normal retry budget because the probe can take several minutes. A healthy S3 listener alone does not establish Git compatibility.

## Updates

`BUZZ_IMAGE` controls both relays and defaults to `ghcr.io/block/buzz:latest`, following stable relay releases. SeaweedFS also follows upstream `latest`, per repository policy. Existing `.env` or Portainer image overrides remain in effect. Moving tags trade reproducibility for lower version-bump maintenance; record exact running versions/digests and retain the old images before stateful changes. A previously passing probe is not sustained-reliability evidence or admission of a later image.

Review client/storage compatibility, take a recoverable backup, pull **all** stack images, then redeploy deliberately. Image availability checks are not enough: wait for initialization, the probe and relay readiness, then exercise Git and media. In Portainer, enable re-pulling only for the approved deployment window. Database migrations run automatically; reverting an image alone may not undo state changes.

## Backup and restore

Back up application and storage state as one write-quiesced checkpoint. Protect dumps, archives, `.env`, IAM credentials and the owner's `nsec` as sensitive data. Choose backup tooling and destinations authorized for **all** content stored in the deployment; infrastructure access does not grant permission to inspect or copy restricted channels or agent-owned data.

1. Stop external writers and both relays; pause any scheduled writers. Keep Postgres running long enough to create a native custom-format dump:

   ```bash
   docker compose --env-file buzz/.env -f buzz/docker-compose.yml stop buzz-relay buzz-pair-relay
   # Pre-create a private backup directory; do not use a public/shareable location.
   umask 077
   docker compose --env-file buzz/.env -f buzz/docker-compose.yml exec -T buzz-postgres \
     sh -ec 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > /srv/private-backup/buzz-postgres.dump
   ```

   Check the command succeeded and the dump is usable before continuing; do not treat a redirected empty/partial file as a backup.
2. Stop SeaweedFS, Redis and Postgres. With no writers left, archive the **entire** SeaweedFS volume and Redis volume using read-only mounts. Retain Git volume state as well for release compatibility; current Git object-storage implementations can rebuild their cache. Record archive checksums, Compose revision, image IDs/digests and matching secret configuration. Never copy a live LevelDB tree as a consistent backup.
3. Restore first into **separate empty volumes and an isolated network**, using the recorded compatible images. Extract the SeaweedFS archive into its `/data` mount, not over the container root; preserve file ownership/modes. Restore the Postgres dump with native `pg_restore` into a fresh database and restore matching Redis state. Do not merge archives into an already-populated store.
4. Start storage, database and Redis, then the relays. Require the unchanged conformance probe and readiness to pass. Compare object counts and content hashes with the checkpoint, clone/fetch every retained repository/ref, verify attachment bytes and test new Git/media writes. Only then accept the recovery checkpoint. Do not start an isolated restore with live routing, production network membership or outbound writers enabled.

## Migration from MinIO and rollback

**This Compose change does not migrate data.** `stacksmith_buzz_minio_data` is deliberately not reused or mounted; Docker retains the old named volume when its declaration is removed. Do not run `down -v`, prune volumes or remove the old store. Deploying this revision against an existing database before copying its objects would leave existing media and Git content unavailable.

Plan a distinct cutover with the deployment owner:

1. Keep automatic deployment disabled. Establish an alternate communication path if this stack hosts the working conversation. Agree the migration scope and who may handle restricted content before any production reads, exports or copies.
2. Retain the old Compose revision, environment, MinIO volume and recoverable images/archives. Create a separate SeaweedFS destination; MinIO's on-disk format is **not** portable to SeaweedFS.
3. Validate the destination with synthetic data first. At cutover, stop all writers and take a consistent recovery checkpoint. An authorized operator transfers **every** application object through the S3 APIs, not by copying MinIO volume files. Do not assume that only attachments are stored there: Git packs, manifests and pointers must move too.
4. Check the complete source/destination key set, sizes and byte hashes (ETags are not portable checksums), metadata and any bucket policy/versioning requirements. Recheck conditional-write behavior on the destination. Switch the relay only after verification, then validate existing Git refs/clones and attachment reads before reopening writes.
5. Retain the original MinIO storage untouched for the agreed rollback window. Rollback before accepting new writes restores the old Compose/images and matching checkpoint. **After new writes, merely switching back loses those writes**: stop writers and reconcile through an approved recovery plan first. Remove old storage and re-enable automation only by a separate deliberate decision.

Tailscale access required. HTTPS via Traefik, with no direct host ports. Relay membership and authenticated media reads are required by default.
