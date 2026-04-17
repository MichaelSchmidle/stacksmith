# LiteLLM Stable Frontend

Stable OpenAI-compatible frontend for local inference backends.

In the current Stacksmith plan, LiteLLM sits in front of `vllm/` on `inf1-ein` so clients can keep talking to one stable hostname and one stable model alias even if the actual backend model changes.

## What this stack is for

- expose a single stable client endpoint
- keep client API keys and base URLs stable
- map friendly aliases like `chat-main` to the currently deployed backend model
- optionally add a second embeddings alias later without changing clients again

## Environment Configuration

```bash
cp litellm/.env.example litellm/.env
```

Important settings:

- `LITELLM_HOSTNAME` - Traefik hostname for the proxy
- `LITELLM_MASTER_KEY` - client-facing API key for LiteLLM (must start with `sk-`)
- `LITELLM_CHAT_ALIAS` - stable model name clients should use, e.g. `chat-main`
- `LITELLM_UPSTREAM_MODEL` - backend model name exposed by vLLM, e.g. `gemma31-main`
- `LITELLM_VLLM_API_BASE` - internal vLLM URL, usually `http://vllm:8000`

## Deployment

Deploy together with Traefik + vLLM:

```bash
docker compose -f traefik/docker-compose.yml -f vllm/docker-compose.yml -f litellm/docker-compose.yml up -d
```

## Client Model Names

Recommended client-facing aliases:

- `chat-main` - primary chat model
- `embed-main` - future embeddings model

This keeps client configuration stable even when the backend model changes.

## Notes

- This stack exposes LiteLLM through Traefik on the **Tailscale-only** entrypoint by default
- vLLM remains the actual model runtime behind LiteLLM
- For Gemma-family backends, `LITELLM_SUPPORTS_SYSTEM_MESSAGE=false` is a sensible default
