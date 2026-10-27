# Tallyport

Deterministic bank-statement intake: CSV files are validated, routed to an
explicitly mapped account, imported through Sure's API, verified and archived.
[Application source and runtime documentation](https://github.com/MichaelSchmidle/tallyport)
(currently private; authorized repository access required).

This is deployment wiring only. Portainer deploys this subfolder and pulls the
prebuilt `ghcr.io/michaelschmidle/tallyport:latest` image. It does not build the
application. The initial image must be published before first deployment.
No UI, published ports, Traefik labels or shared `stacksmith` network are needed;
the default isolated bridge needs outbound access to the configured Sure HTTPS URL.

Resource defaults are 0.5 CPU, 256 MiB and 64 PIDs. Override them through
`TALLYPORT_CPU_LIMIT`, `TALLYPORT_MEMORY_LIMIT` and `TALLYPORT_PIDS_LIMIT` in private
deployment settings rather than editing the template.

## Private image access

The application repository and container package start private. Register GHCR in
Portainer using an identity authorized to read the package (`read:packages` where
applicable), then verify a pull on the target Docker environment. Repository access
alone does not prove package access. Never put registry tokens in this repository
or the application's configuration. Verify package visibility after publication.

## Private configuration and mounts

Set the four required path variables from `.env.example` in private deployment
settings or Portainer. These are **Docker-host** paths, not paths on the Portainer
server or a workstation. Missing bind sources fail rather than create directories.

- `TALLYPORT_CONFIG_FILE`: existing private TOML configuration, including the Sure
  URL, supported Sure version, explicit account mappings and container paths.
- `TALLYPORT_API_KEY_FILE`: existing UTF-8 file containing only a dedicated Sure
  API key. It is mounted read-only; the key never belongs in Compose variables.
- `TALLYPORT_INTAKE_DIR`: the already mounted, restricted bank-import share. Keep
  it separate from document-consumer intake. Grant access only to this share,
  not the NAS root or unrelated document/backup shares.
- `TALLYPORT_STATE_DIR`: existing local persistent directory for the SQLite
  journal and worker lock; **not SMB/NFS**.

Configure `intake = "/intake/inbox"`, `archive = "/intake/processed"`,
`quarantine = "/intake/rejected"` and `state = "/state"`. Set
`key_file = "/run/secrets/sure_api_key"` (without `key_env`). The configuration
is mounted at the image default `/config/config.toml`. Use the source repository's current
configuration example rather than inventing mappings. Unknown accounts fail
closed; this stack creates neither Sure accounts nor NAS shares.

The fixed runtime UID/GID is **10001:10001**. Prepare the local state directory
with mode 0700, and configuration/key files with 0400 (or equivalent restrictive
ACLs). Map the NAS mount's permissions to the runtime owner. For SMB this involves
credentials and mount ownership options; NFS uses export rules and numeric
UID/GID mapping. Do not make secrets world-readable or run as root to work around
permissions. The image runs with a read-only root filesystem and writable state
and intake mounts only (plus a small temporary filesystem).

`create_host_path: false` rejects a missing path, but does not prove a NAS is
mounted at an existing directory. The host's mount/service dependency must fail
closed too: prove the underlying unmounted directory is not writable by the
runtime UID, and exercise mount-loss/recovery before enabling unattended use.
Also prove that the target share supports no-replace hardlink publication and
directory `fsync`, which the importer requires for safe archival. Local filesystem
tests do not establish NAS compatibility; unsupported operations retain files for
retry rather than silently weakening durability.

## Deployment and acceptance

After the image exists, private settings are ready and live operation is approved:

```sh
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
```

Starting the worker is permission to import files in the inbox. Do not start it
against live data just to check container health. First use a separately scoped
synthetic test account/intake and verify import, repeated-file handling and
restart recovery. Container liveness is not successful import evidence.
Verify DNS resolution, Tailscale routing, TLS hostname validation and the actual
Sure API flow from the worker's container network, not merely from its host. The
default bridge does not itself establish reachability to a tailnet-only endpoint.

Configuration errors exit 4; `restart: unless-stopped` then restarts the container
with Docker's backoff. A repeatedly restarting container is not a healthy worker:
stop the stack, correct its private configuration/permissions and validate before
starting it again.

Use one worker and one durable state directory for a given intake. Complete
files should be published by copying under a temporary extension and renaming to
`.csv`; stable-file polling is an additional guard, not proof that a paused copy
is finished. Malformed files are rejected, while transient connectivity failures
remain available for retry. See the application documentation for exact CLI,
configuration, error codes and manual requeue procedure.

Sure's `read_write` API key is broader than an import-only capability. Account
mapping restricts what this utility intends to write, not the key's server-side
permissions. Keep the credential private and use a dedicated authorized identity
where practical. Content-free logs do not make original files, mappings or the
journal non-sensitive; agree access, retention and encrypted backups separately.

## Updates, recovery and removal

`latest` follows Stacksmith's rolling application-image policy. The tag itself
schedules no pulls: Portainer's pull/redeployment policy is separate. Record the
running image digest and preserve a compatible state/configuration checkpoint
before updates. Initial publication and later schema-changing updates still need
acceptance; rolling a tag back does not reverse journal migrations.

For a consistent simple checkpoint, stop the worker and preserve the entire state
directory (including SQLite sidecars), configuration, intake/archive state and the
matching image identity in an approved protected destination. Preserve the key
through the operator's secret store. This bundle installs no backup scheduler.

To pause, stop the stack. To remove, stop/remove the stack while retaining the
host-mounted state, configuration, key and original files until their disposition
is explicitly agreed. Removing the importer does not remove transactions already
written to Sure. A batch can be partly written during an interruption; safe retry
and readback, not an all-or-nothing bank import, are the recovery contract.
