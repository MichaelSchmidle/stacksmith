# Host-local infrastructure maintenance

A deterministic Python-standard-library job, run daily by systemd on each Docker
host. No SSH, extra accounts, API keys, LLM runtime, third-party Python packages,
workload inventory, global Docker prune or volume cleanup.

## Scope and ownership

The operator owns the root-installed job and its nonsecret local configuration.
Keep the source here until it is replaced or deliberately retired. Updates to this
source do **not** update installed copies: review, validate and reinstall explicitly.
Merging this tool does not itself deploy it or change any Compose service.

- **Portainer Agent:** only the existing standalone container named
  `portainer_agent`, using an explicit stable `portainer/agent:X.Y.Z` image. Match
  the running server version from its configured HTTPS `/api/status` endpoint.
  Refuse automatic downgrades, stopped/unhealthy agents, unexpected repositories,
  Compose-managed agents, concurrent runs and untracked rollback containers.
- **Optional Traefik:** only `stacksmith_traefik`, using its existing
  `traefik:latest` image and canonical local Compose project. The project must
  contain only `portainer` and `traefik`; recorded ownership and the rendered
  Traefik configuration hash must match. Pull only Traefik, recreate it with
  `--no-deps --pull never`, and verify the HTTPS Portainer application route.
- **Portainer Server is deliberately not auto-updated by this tool.** Server
  updates can migrate persistent data. Arrange owner-managed, tested recovery
  coverage before adding this capability; retaining an old image is not enough.
  This tool never reads, copies or backs up the Portainer data volume.

Agent discovery uses one named container, not a daemon-wide container listing.
State contains image/container IDs and transaction metadata, not environment
values or volume contents. The replacement payload stays in memory and preserves
agent settings, mounts, restart policy and networks. A transaction label binds
recovery to this job's replacement; an unexpected replacement is not deleted.
No running application container is removed.

## Prerequisites

Linux with systemd, Python 3.10+, Docker Engine and the Docker CLI; the optional
core host also needs Docker Compose supporting `config --hash`. The agent must
publish `127.0.0.1:9001` for its local health check. Preserve any existing
Tailscale Serve listener and the internal Docker network used by a same-host
Portainer Server; this job changes neither tailnet policy nor listener setup.

The version URL must work without authentication from every host, with valid
HTTPS and no redirect. The only TLS-verification exception is the agent's
self-signed **loopback** `/ping` endpoint. No network bypass is used for the server.
Root and access to Docker are required; Docker socket access is effectively root.
The optional Compose project and environment files remain under the deployment
owner's control. No production environment values belong in this repository.

## Install on each host

Choose a trusted local checkout and copy one of the example configurations,
editing the HTTPS management hostname and, on the core host only, the real
Compose paths/project. No credentials are required. Run these commands from this
directory:

```sh
sudo install -D -o root -g root -m 0755 maintain.py /usr/local/libexec/stacksmith-maintenance.py
sudo install -D -o root -g root -m 0644 config.example.json /etc/stacksmith-maintenance.json
sudo install -D -o root -g root -m 0644 stacksmith-maintenance.service /etc/systemd/system/stacksmith-maintenance.service
sudo install -D -o root -g root -m 0644 stacksmith-maintenance.timer /etc/systemd/system/stacksmith-maintenance.timer
# Edit the installed config; use config.core.example.json as the optional core-host shape.
sudoedit /etc/stacksmith-maintenance.json
sudo systemd-analyze verify /etc/systemd/system/stacksmith-maintenance.service /etc/systemd/system/stacksmith-maintenance.timer
sudo python3 /usr/local/libexec/stacksmith-maintenance.py --check
sudo systemctl daemon-reload
sudo systemctl start stacksmith-maintenance.service
sudo systemctl enable --now stacksmith-maintenance.timer
```

Daily at 04:00 UTC plus up to 15 minutes jitter by default. `Persistent=true` runs a
missed occurrence after the timer returns. To choose a different schedule, use a
timer drop-in and reset `OnCalendar=` before specifying its replacement. If server
automation is later added, schedule the core host before agent-only hosts; this
is not a coordinated fleet rollout and one host's failure does not stop others.

`--check` performs preflight without pulling or mutating Docker resources; it
creates the local state directory/lock if absent. The normal agent path does not
pull or recreate an already-current agent. The Traefik path pulls its moving tag,
but does not recreate an unchanged image or apply a changed Compose configuration.
A normal successful no-change run verifies runtime access, not the upgrade path.

## Failure, recovery and cleanup

A durable root-only journal is written before replacing an agent or Traefik.
Agent failure restores the original stopped container, preserving its identity.
Traefik failure restores the previous image tag and recreates through the same
Compose project. Signals/timeouts trigger best-effort rollback; a crash or power
loss can require the next invocation to recover. A recovery invocation reports
failure after rollback rather than immediately retrying the same upgrade.
Do not promise uninterrupted management/routing or guaranteed rollback from this.

After successful health verification, remove only the stopped transaction-owned
agent rollback container, with no volume deletion. Retain the previous image for
rollback. Older image IDs recorded by **this job** become cleanup candidates only
after a later successful upgrade. Keep current/previous images, skip images with
unrelated repository tags, and never force deletion of referenced images. Existing
untracked image clutter is not adopted or globally pruned. A failed image pull
leaves the running container alone.

On ambiguous identity, changed Compose configuration or failed recovery, stop
and preserve the journal for the operator. Inspect only this job's state and the
named infrastructure services. Do not delete its journal or rollback container
just to make the next run green. Disabling a timer does not undo completed updates.

```sh
systemctl status stacksmith-maintenance.service stacksmith-maintenance.timer
systemctl list-timers stacksmith-maintenance.timer
journalctl -u stacksmith-maintenance.service
sudo python3 /usr/local/libexec/stacksmith-maintenance.py --check
```

Failures are visible through a nonzero service result and the journal. This tool
does not install an alert transport; connect existing monitoring if push alerts
are required. Local agent `/ping` verifies the running version, not Portainer's
authenticated server-to-agent connection. Verify that separately during rollout;
the UI can lag its live version header by several minutes.

To disable: `sudo systemctl disable --now stacksmith-maintenance.timer`.
To uninstall, first stop/verify the named service and resolve any pending
transaction; remove only its two unit files, installed script and configuration,
then run `systemctl daemon-reload`. Retain `/var/lib/stacksmith-maintenance` and the
previous images until recovery information is no longer needed. No application
volumes, Tailscale configuration or Docker networks are removed.

## Tests

```sh
python3 -m unittest discover -s _tools/maintenance -v
```

The deterministic suite uses a fake Docker model, not production data. It covers
version/input validation, no-op/check behavior, mount/network preservation,
upgrade failure, journal recovery, ownership conflicts, scoped cleanup, Compose
ownership/configuration guards, targeted recreation and Traefik rollback.
Live preflight/timer execution, actual image replacement and failure-injection
coverage must be reported separately; unit tests are not fleet deployment proof.
