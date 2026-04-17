# Repository Guidelines

## Project Structure & Module Organization
This repository is a modular Docker Compose stack. The root [`docker-compose.yml`](/home/michael/stacksmith/docker-compose.yml) defines the Portainer management service. [`traefik/`](/home/michael/stacksmith/traefik) contains the reverse proxy stack plus dynamic config in `traefik/dynamic/`. Each optional service lives in its own top-level directory such as [`pihole/`](/home/michael/stacksmith/pihole), [`n8n/`](/home/michael/stacksmith/n8n), or [`arr/`](/home/michael/stacksmith/arr), and should include `docker-compose.yml`, `.env.example`, and `README.md`.

## Build, Test, and Development Commands
Use Docker Compose directly; there is no separate build system.

- `docker network create stacksmith`: create the shared external network once.
- `cp .env.example .env && cp traefik/.env.example traefik/.env`: create local config templates.
- `docker compose -f docker-compose.yml -f traefik/docker-compose.yml up -d`: start the core management stack.
- `docker compose -f traefik/docker-compose.yml -f servicename/docker-compose.yml up -d`: add one service stack.
- `docker compose -f traefik/docker-compose.yml -f servicename/docker-compose.yml config`: validate merged Compose files before committing.
- `docker compose logs -f servicename`: inspect runtime behavior.

## Coding Style & Naming Conventions
Compose files use 2-space YAML indentation. Keep service directories lowercase (`uptimekuma/`), env vars uppercase (`TRAEFIK_HOSTNAME`), and container names prefixed with `stacksmith_` (for example `stacksmith_portainer`). Prefer env-driven configuration over hard-coded values. New routed services should join the external `stacksmith` network and use Traefik labels patterned after existing services, typically with the `websecure-tailscale` entrypoint and `secure-headers@docker` middleware. Default `TZ` in `.env.example` files should remain `Europe/Zurich`.

## Testing Guidelines
There is no automated test suite in this repo. Validation is operational: run `docker compose ... config` for syntax, then bring up the affected stack locally and verify logs, routing, and service reachability. When testing locally, use copied `.env` files only; never commit secrets or read production `.env` values into documentation.

## Commit & Pull Request Guidelines
Recent history follows short imperative subjects, often in Conventional Commit style: `fix: ...`, `chore: ...`, `traefik: ...`, `revert: ...`. Keep commits scoped to one service or infrastructure change. PRs should explain what changed, list affected compose files and env templates, note any required manual configuration, and include screenshots only when a UI change or dashboard exposure is relevant.
