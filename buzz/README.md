# Buzz Stack

[Buzz](https://github.com/block/buzz) is a self-hosted workspace for humans and AI agents. This stack runs the relay and device-pairing service with Postgres, Redis, and MinIO behind Traefik.

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

## Updates and Storage

- `BUZZ_IMAGE` controls both relays and defaults to `ghcr.io/block/buzz:latest`, which follows stable relay releases. Existing `.env` or Portainer overrides remain in effect; update or remove them to use `latest`.
- Review client compatibility, back up, and rerun the deployment commands to update. In Portainer, enable image re-pulling. For reproducible deployments, pin a tested image digest.
- Postgres, Redis, MinIO, and Git data persist in the four `stacksmith_buzz_*_data` volumes. Back up Postgres with a database dump and capture the remaining data while writes are stopped; retain `.env` and the owner's `nsec` securely.
- Database migrations run automatically; reverting the image alone may not undo them.

Tailscale access required. HTTPS via Traefik, with no direct host ports. Relay membership and authenticated media reads are required by default.
