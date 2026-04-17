# LiteLLM Stable Frontend

Stable OpenAI-compatible frontend for local inference backends.

This stack is designed to run as **one persistent LiteLLM instance** with runtime-managed model aliases. Model mappings are stored in the database, so you can add/update aliases through the UI, API, or CLI without editing source files or restarting the proxy.

## What this stack is for

- expose a single stable client endpoint
- keep client API keys and base URLs stable
- map friendly client-facing aliases like `main`, `code`, `fast`, or `embed-main` to whatever backend models are currently deployed
- persist those mappings across restarts via Postgres

## Environment Configuration

```bash
cp litellm/.env.example litellm/.env
```

Important settings:

- `LITELLM_HOSTNAME` - Traefik hostname for the proxy
- `LITELLM_MASTER_KEY` - client-facing admin/master key for LiteLLM (must start with `sk-`)
- `LITELLM_DB_*` - Postgres settings for persistent runtime configuration

## Deployment

Deploy together with Traefik:

```bash
docker compose -f traefik/docker-compose.yml -f litellm/docker-compose.yml up -d
```

## Runtime Model Management

This stack intentionally starts with an empty `model_list` and `store_model_in_db: true`.

The bootstrap config is generated inside the container at startup, so Git/Portainer deployments do not depend on a fragile single-file bind mount. The bootstrap shell now lives in the container `entrypoint` itself, which avoids both the image's default `litellm` entrypoint and Portainer/stack parsing edge cases.

That means you can add aliases/models at runtime via:

- LiteLLM UI (`/ui`)
- LiteLLM API (`POST /model/new`)
- LiteLLM management CLI

Examples of aliases you might create later:

- `main` -> primary chat backend
- `code` -> coding-focused backend
- `fast` -> smaller/faster backend
- `embed-main` -> embeddings backend

## Operating Model

- Run one LiteLLM instance per trust boundary / client endpoint, not per backend model
- Run as many backend services as you need behind it (for example multiple vLLM deployments)
- Let Traefik expose LiteLLM as the stable front door

## Notes

- This stack exposes LiteLLM through Traefik on the **Tailscale-only** entrypoint by default
- The Postgres sidecar is only for LiteLLM metadata / configuration persistence
- STT/TTS are typically separate services behind Traefik, not routed through LiteLLM unless you have a strong reason to unify them there
