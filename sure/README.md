# Sure personal finance

Self-hosted [Sure](https://sure.am/) with a browser UI and an authenticated
[MCP endpoint](https://github.com/we-promise/sure/blob/main/docs/hosting/mcp.md)
for an external financial assistant. Uses upstream images only; no bundled agent,
local model server, AI proxy, bank credentials or automatic backup service.

## Components and exposure

- `sure`: Rails web app, routed through the existing tailnet-only Traefik
  `websecure-tailscale` entrypoint to port 3000. No published host ports.
- `sure-worker`: Sidekiq background jobs. Starts after the web health check, so
  the web entrypoint has completed database preparation first. Has a dedicated
  outbound bridge, not access to the shared `stacksmith` Docker network.
- `sure-db`: PostgreSQL 16, matching the upstream Compose major version.
- `sure-redis`: Redis 7 with AOF persistence for background jobs.

Database and Redis only join the internal `sure-backend` network. Storage is
shared by the web app and worker at `/rails/storage`. This is network separation,
not protection from the Docker host administrator.

**Image policy:** use the rolling `ghcr.io/we-promise/sure:stable` channel for
both web and worker. This is an intentional exception to the repository's usual
`latest` application policy: upstream documents `latest` as its alpha channel.
It is not a fixed version pin. Record image identities before updates and keep
both app services on the same resolved image. PostgreSQL stays on major 16;
changing its major requires a separate data migration.

## Portainer deployment

Prerequisites: Docker Standalone with Compose support, an existing external
`stacksmith` network, the standard Traefik router/middleware/certificate setup,
and DNS pointing your chosen finance-service hostname to that tailnet router.
Use one instance of this bundle per Docker host because names are fixed.

After this bundle is merged:

1. In the intended Portainer environment, add a Git-backed stack named `sure`.
2. Repository: `https://github.com/MichaelSchmidle/stacksmith`, reference
   `refs/heads/main`, Compose path **`sure/docker-compose.yml`**.
3. Copy variable names from `.env.example` into Portainer's environment settings.
   The example is a template, not a file Portainer loads automatically.
4. Set `SURE_HOSTNAME` (hostname only), `TZ`, `SURE_SECRET_KEY_BASE` and
   `SURE_DB_PASSWORD`. Generate independent secrets in a trusted terminal:
   `openssl rand -hex 64` for the Rails secret and `openssl rand -hex 32` for
   the database password. Empty required values fail Compose validation.
5. Leave **both** `SURE_MCP_API_TOKEN` and `SURE_MCP_USER_EMAIL` empty initially.
   Deploy, then create the first owner account through HTTPS. Immediately close
   self-service registrations under **Settings → Self-Hosting → Onboarding**.
   That onboarding setting lives in the database, not in this Compose file.
6. Create/invite the intended assistant's own Sure user into the appropriate
   family and grant the required application-level account access. Generate a
   separate MCP token, set both MCP variables, and redeploy through Portainer.
7. Test browser access and MCP before importing real financial data. Configure
   and restore-test an owner-approved backup destination before relying on it.

No service is deployed and no assistant is configured merely by adding these
files. Keep hostname, secrets and private operator details in Portainer, not Git.
For an initial deployment, prefer manual updates until the acceptance checks pass.

## MCP access and ownership

Endpoint: **`https://<SURE_HOSTNAME>/mcp`**, authenticated with
`Authorization: Bearer <SURE_MCP_API_TOKEN>`. Both environment variables are
required for this static-token route; the configured email must identify an
existing user. Sure also supports OAuth; do not configure an additional OAuth
integration unless intended. Removing the static token does not revoke separately
issued OAuth tokens.

MCP includes write access to financial **records**. Inspection of the
[v0.7.5-hotfix.2 registry](https://github.com/we-promise/sure/blob/v0.7.5-hotfix.2/app/models/assistant.rb)
and its write functions found no tool for initiating/authorising a bank payment
or placing a brokerage order. `create_transaction` and `delete_transaction`
change the local ledger. The preview `record_bill_payment` function records a
payment/settlement in Sure; it does not send money. That remains consequential:
it can make an unpaid bill look paid if misused.

The MCP controller dispatches only registered tools, including per-user preview
gates. It does not provide a general per-tool allowlist setting. Treat this as
an inspected-release capability boundary, not an immutable guarantee: inspect
`tools/list` and changed write implementations after upgrades. If a future tool
can move money or place orders, do not expose it without explicit owner approval
and an enforced restriction. A prompt instruction alone is not that restriction.

The financial assistant can own imports, categorisation, reconciliation, budgets
and routine application upkeep within its agreed authority. MCP does **not**
grant Docker/Portainer lifecycle control. Agree a separate scoped maintenance
route before delegating upgrades, backups or recovery; do not hand over a
host-wide Docker socket or administrator token as part of enabling MCP.

No model-provider keys are passed by this bundle. MCP itself does not require
Sure's in-app AI provider. Some tools, notably PDF statement extraction and
semantic document search, depend on additional provider setup and may be
unavailable until configured. Do not add model credentials merely to make every
tool work. Data returned to an external assistant can reach its inference
provider; self-hosting Sure does not change that.

Designate storage, database, Redis, backups, logs and assistant credentials as
protected financial resources. Status-only infrastructure operations are not
permission to read records. Restrict Portainer access accordingly; secrets in
environment variables are still visible to privileged operators.

## Validation and acceptance

From the repository root for a local/manual deployment:

```bash
cp sure/.env.example sure/.env
# Fill required values locally; do not commit this file.
docker compose --env-file sure/.env -f sure/docker-compose.yml config -q
docker compose --env-file sure/.env -f sure/docker-compose.yml pull
docker compose --env-file sure/.env -f sure/docker-compose.yml up -d
```

Through Portainer, use that stack's services and logs instead of launching a
second, unmanaged Compose project. Expected: database and Redis healthy, then
web healthy, then worker running without repeated startup errors. `/up` is a
Rails boot check, not evidence that imports, jobs or backups work correctly.

Acceptance checks:

- Routed HTTPS browser sign-in works from the intended client, with registration
  closed after the owner is established; no direct app/database/Redis host ports.
- Unauthenticated MCP returns 401. Authenticated `initialize`, `tools/list` and
  a read work as the intended user. Use `tools/list` as the deployed capability
  inventory; preview tools depend on that user's settings.
- A reversible write against synthetic records succeeds, is visible in the UI,
  and can be corrected. Separately inspect tools for payment/order execution.
- Import a representative statement, then repeat it to check duplicate handling;
  reconcile balances, transfers and currencies against the source.
- Confirm a background job completes and survives an ordinary restart where
  applicable. Prove backup/restore on separate, empty storage before real use.

Do not infer support for a particular Swiss bank, CAMT variant or broker from
Sure's generic provider coverage. Validate the actual export/provider separately.

## Update and recovery

Use Portainer to update a Portainer-owned stack. Pulling/redeploying a Git-backed
stack can update images and run database migrations; a Git merge alone is not
proof that a new image is running. Before updating:

1. Record app version and exact image IDs/digests for web and worker.
2. Stop writes and background workers; take a coherent backup of the database,
   uploaded storage, Redis queue state, and deployment secrets/configuration.
3. Preserve the previous image artifact or a pullable digest.
4. Redeploy both app services together and repeat health, MCP inventory and
   synthetic read/write checks. Reassess new permissions before normal agent use.

Persistent volumes:

| Volume | Contents | Recovery requirement |
|---|---|---|
| `stacksmith_sure_db` | Accounts, ledger, settings and users | PostgreSQL-consistent dump or cold backup |
| `stacksmith_sure_storage` | Uploaded documents and app storage | Archive while app and worker writes are stopped |
| `stacksmith_sure_redis` | Background-job queue/AOF | Cold archive with Redis stopped after writers stop |

A manual database dump for a Compose-owned installation can use
`docker compose --env-file sure/.env -f sure/docker-compose.yml exec -T sure-db pg_dump -U sure -d sure -Fc > database.dump`.
Use a private destination, stop app/worker writes first, and separately preserve
the other volumes and secrets. A database dump alone is not a full backup.
This bundle does not schedule or verify backups automatically.

Restore into isolated empty volumes using the same recorded application image
and PostgreSQL major. Restore the database with `pg_restore`, restore storage and
Redis before starting workers, and keep the original Rails secret. Verify login,
ledger totals, uploaded documents and queue behaviour. Do not overwrite the
working instance for a restore test. Reverting an image does not undo database
migrations: recovery may require restoring the entire pre-upgrade checkpoint.
Never use `down -v` on an installation containing data you intend to keep.

Upstream: [repository](https://github.com/we-promise/sure),
[Docker hosting guide](https://github.com/we-promise/sure/blob/main/docs/hosting/docker.md),
[MCP documentation](https://github.com/we-promise/sure/blob/main/docs/hosting/mcp.md).
