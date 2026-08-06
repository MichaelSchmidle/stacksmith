# Buzz Stack

Buzz is a self-hostable workspace where humans and AI agents share channels, threads, canvases, workflows, and a signed event log. This Stacksmith bundle runs the Buzz relay and its bundled invite web surface with Postgres, Redis, and MinIO behind the existing Tailscale-only Traefik entrypoint. The full collaboration UI remains a native Buzz Desktop client; the optional Git repository browser is not enabled for this pilot.

Official sources:

- [Buzz repository](https://github.com/block/buzz)
- [Upstream production Compose bundle](https://github.com/block/buzz/tree/main/deploy/compose)
- [nak Nostr key utility](https://github.com/fiatjaf/nak)
- [Hermes Buzz integration](https://hermes-agent.nousresearch.com/docs/integrations/buzz)

## Security model

- The relay is not published on a host port. Traefik is its only ingress path.
- Relay membership, auth-token checks, and authenticated media reads are enabled by default.
- Postgres, Redis, and MinIO use an internal Docker network and are not joined to `stacksmith`.
- Use a dedicated Nostr identity for every human and agent. Never reuse the relay signing key as a user or agent key.
- Keep Hermes agents owner-only or explicitly allowlisted. Buzz-managed ACP runtimes may auto-approve host tool execution; broad channel access can therefore become broad shell access.

## Bootstrap

### 1. Generate identities and secrets

Generate the owner identity with a NIP-19-aware tool such as `nak`, which emits the `nsec` format accepted by Buzz Desktop:

```bash
OWNER_SECRET_HEX="$(nak key generate)"
printf '%s\n' "$OWNER_SECRET_HEX" | nak encode nsec
printf '%s\n' "$OWNER_SECRET_HEX" | nak key public
unset OWNER_SECRET_HEX
```

Immediately store the displayed `nsec` in a password manager and import it through Buzz Desktop's **Use an existing key** flow. Put the displayed 64-character hex public key in `BUZZ_RELAY_OWNER_PUBKEY`.

Generate a separate relay keypair using the pinned Buzz image:

```bash
docker run --rm --entrypoint buzz-admin \
  ghcr.io/block/buzz:sha-96ae141@sha256:472e9cf7cfee069198ea038a923ed63cbaea48954615f082d6c82149f5917975 \
  generate-key
```

Put its 64-character hex private key in `BUZZ_RELAY_PRIVATE_KEY`; do not import or use the relay identity as a participant.

Generate the remaining secrets with a cryptographically secure password manager or:

```bash
openssl rand -hex 32
```

Use distinct values for the Git hook HMAC secret, database password, Redis password, and S3 credentials.

### 2. Configure

```bash
cp buzz/.env.example buzz/.env
```

Replace every `CHANGE_ME` value and set `BUZZ_HOSTNAME` to a private hostname routed to the Stacksmith Traefik instance. Do not commit `buzz/.env`.

The pilot image is upstream commit `96ae141` (`sha-96ae141`) pinned to its immutable multi-architecture digest. Upstream publishes relay images from `main`/`sha-*`; GitHub's semver releases currently describe Desktop releases rather than a corresponding relay image. Update the commit and digest deliberately; do not use a floating tag for unattended deployment.

### 3. Validate and deploy

```bash
docker compose --env-file buzz/.env -f buzz/docker-compose.yml config
docker compose --env-file buzz/.env -f buzz/docker-compose.yml up -d
docker compose --env-file buzz/.env -f buzz/docker-compose.yml ps
```

The owner configured by `BUZZ_RELAY_OWNER_PUBKEY` is bootstrapped automatically. Enroll every additional human and each agent's distinct Nostr public key before enabling their clients:

```bash
docker compose --env-file buzz/.env -f buzz/docker-compose.yml exec buzz-relay \
  buzz-admin add-member --pubkey <NPUB_OR_HEX_PUBKEY> --role member

docker compose --env-file buzz/.env -f buzz/docker-compose.yml exec buzz-relay \
  buzz-admin list-members
```

Hermes agents must each use a separate Buzz private key whose corresponding public key is enrolled above. Prefer the owner-controlled invite/NIP-OA flow once validated; `buzz-admin add-member` is the explicit operator bootstrap path.

Connect Buzz Desktop to `wss://<BUZZ_HOSTNAME>`. The HTTPS hostname serves Buzz's invite landing surface, not the full channel workspace or the optional Git repository browser.

## Agent-room pilot

A conservative creative-room setup starts with three agent identities and one channel:

- require explicit mentions before an agent is triggered;
- let an activated agent read recent room history before contributing;
- allow at most one contribution and one targeted handoff per activation;
- disable heartbeat chatter and broad automatic replies;
- keep manuscripts and canonical project state outside Buzz until the pilot proves useful.

For an existing Hermes deployment, prefer Hermes' native Buzz gateway adapter over Buzz Desktop's managed ACP runtime. It preserves Hermes memory, skills, sessions, cron, and approval behavior while Buzz remains the room and transport.

## Persistence and backup

| Volume | Purpose |
|---|---|
| `stacksmith_buzz_postgres_data` | Events, memberships, search, workflow state, and metadata |
| `stacksmith_buzz_redis_data` | Redis persistence and coordination state |
| `stacksmith_buzz_minio_data` | Uploaded media, artifacts, and content-addressed Git objects |
| `stacksmith_buzz_git_data` | Local Git repositories, worktrees, and cache state |

Back up all four volumes together with the `.env` secrets and the owner's encrypted `nsec` backup held outside the stack. The public owner key in `.env` cannot recover ownership by itself.

Capture Postgres with an application-consistent database dump. Take the remaining state during a quiesced maintenance window or with coordinated snapshots; copying unrelated live volumes independently is not a reliable backup. Periodically test a full restore, including owner login, memberships, media, and Git data.

## Update

1. Review Buzz release notes and changes under `deploy/compose/`.
2. Resolve the desired relay image to an immutable multi-architecture digest.
3. Update `BUZZ_IMAGE` in `.env.example` and the bootstrap command above.
4. Validate Compose, back up the stack, pull, and redeploy.

Buzz is pre-1.0 and changes quickly. Treat migrations and client/relay compatibility as release work, not routine unattended image refreshes.
