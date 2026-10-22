#!/usr/bin/env python3
"""Host-local Portainer Agent and optional Compose-managed core maintenance.

No SSH, API credentials, volume backups, workload inventories or global pruning.
Portainer Server updates require explicit acceptance of no database rollback.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import http.client
import json
import os
from pathlib import Path
import re
import socket
import signal
import ssl
import subprocess
import sys
import time
from urllib.parse import quote, urlsplit
from typing import Any
import urllib.error
import urllib.request
import uuid

AGENT = "portainer_agent"
BACKUP = "portainer_agent__stacksmith_previous"
TXN_LABEL = "io.stacksmith.maintenance.transaction"


class Error(RuntimeError):
    pass


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value):
        raise Error("expected a stable numeric server/agent version")
    return tuple(map(int, value.split(".")))


def validate_config(config):
    if not isinstance(config, dict) or set(config) - {"status_url", "core"}:
        raise Error("unknown maintenance configuration keys")
    u = urlsplit(config.get("status_url", ""))
    if u.scheme != "https" or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise Error("status_url must be HTTPS without credentials, query or fragment")
    if u.path != "/api/status":
        raise Error("status_url must point to /api/status")
    if "core" in config:
        t = config["core"]
        if (not isinstance(t, dict) or set(t) - {"directory", "project", "files", "portainer_without_backup"}
                or not {"directory", "project", "files"} <= set(t)):
            raise Error("core needs directory, project and files")
        if not isinstance(t.get("portainer_without_backup", False), bool):
            raise Error("portainer_without_backup must be an explicit boolean")
        if not Path(t["directory"]).is_absolute() or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", t["project"]):
            raise Error("invalid Compose project or directory")
        if not t["files"] or any(not Path(p).is_absolute() for p in t["files"]):
            raise Error("Compose files must be explicit absolute paths")
    return config


def log(message):
    print(message, flush=True)


def command(args, *, cwd=None):
    # Do not let a login shell redirect Compose to other files, projects or daemons.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("COMPOSE_", "DOCKER_"))}
    env["DOCKER_HOST"] = "unix:///var/run/docker.sock"
    env["DOCKER_CONFIG"] = "/var/lib/stacksmith-maintenance/docker"
    try:
        p = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, timeout=360)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Error("maintenance subprocess could not complete") from exc
    if p.returncode:
        # Compose errors can contain interpolated configuration; do not emit them.
        raise Error("maintenance command failed: " + " ".join(args[:3]))
    return p.stdout


class UnixConnection(http.client.HTTPConnection):
    def __init__(self):
        super().__init__("localhost", timeout=60)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect("/var/run/docker.sock")


class Docker:
    def request(self, method, path, data=None, *, missing=False) -> Any:
        conn = UnixConnection()
        try:
            body = json.dumps(data).encode() if data is not None else None
            conn.request(method, path, body, {"Content-Type": "application/json"})
            r = conn.getresponse()
            raw = r.read()
            if r.status == 404 and missing:
                return None
            if r.status >= 400:
                raise Error("Docker request failed (HTTP " + str(r.status) + ")")
            return json.loads(raw) if raw else None
        finally:
            conn.close()

    def inspect(self, name, missing=False) -> Any:
        return self.request("GET", "/containers/" + quote(name, safe="") + "/json", missing=missing)

    def image(self, ident) -> Any:
        return self.request("GET", "/images/" + quote(ident, safe="") + "/json", missing=True)

    def supports_multi_network(self):
        version = self.request("GET", "/version")["ApiVersion"]
        return tuple(map(int, version.split("."))) >= (1, 44)

    def pull(self, image):
        command(["docker", "pull", image])

    def stop(self, ident):
        self.request("POST", "/containers/" + quote(ident, safe="") + "/stop?t=20")

    def rename(self, ident, name):
        self.request("POST", "/containers/" + quote(ident, safe="") + "/rename?name=" + quote(name))

    def create(self, name, payload):
        return self.request("POST", "/containers/create?name=" + quote(name), payload)["Id"]

    def start(self, ident):
        self.request("POST", "/containers/" + quote(ident, safe="") + "/start")

    def remove(self, ident):
        # No force, no volume deletion. Running containers must never be removed.
        self.request("DELETE", "/containers/" + quote(ident, safe=""))

    def remove_image(self, ident):
        self.request("DELETE", "/images/" + quote(ident, safe="") + "?force=false&noprune=true")


def agent_payload(old, version, token, image_config):
    version_tuple(version)
    labels = old["Config"].get("Labels") or {}
    if any(k.startswith("com.docker.compose.") for k in labels):
        raise Error("refusing to replace a Compose-managed agent")
    if not old["Config"]["Image"].startswith("portainer/agent:"):
        raise Error("unexpected agent image repository")
    mounts = old.get("Mounts", [])
    binds = {m["Destination"] for m in mounts if m.get("Type") == "bind"}
    if (any(m.get("Type") != "bind" for m in mounts)
            or not set(old["Config"].get("Volumes") or {}) <= binds):
        raise Error("only bind-mounted standalone agents are supported; refusing volume replacement")
    if not isinstance(image_config, dict):
        raise Error("cannot establish the running agent image defaults")
    payload = copy.deepcopy(old["Config"])
    # Inspect merges image defaults with container overrides. Do not freeze the
    # old image's execution settings into every future replacement. Explicit
    # values equal to image defaults are indistinguishable from inheritance.
    for key in ("Entrypoint", "Cmd", "WorkingDir", "User", "StopSignal",
                "StopTimeout", "Healthcheck", "Shell", "ArgsEscaped"):
        if key in image_config and payload.get(key) == image_config[key]:
            payload.pop(key, None)
    inherited_env = {item.split("=", 1)[0]: item for item in image_config.get("Env") or []}
    overrides = [item for item in payload.get("Env") or []
                 if inherited_env.get(item.split("=", 1)[0]) != item]
    if overrides:
        payload["Env"] = overrides
    else:
        payload.pop("Env", None)
    image_labels = image_config.get("Labels") or {}
    labels = {key: value for key, value in labels.items()
              if key not in image_labels or image_labels[key] != value}
    payload["Image"] = "portainer/agent:" + version
    if payload.get("Hostname") == old["Id"][:12]:
        payload.pop("Hostname")
    payload["Labels"] = {**labels, TXN_LABEL: token}
    payload["HostConfig"] = copy.deepcopy(old["HostConfig"])
    networks = {}
    for name, network in old["NetworkSettings"]["Networks"].items():
        # Retain declared IPAM/aliases, not dynamically assigned addresses/IDs.
        n = {k: copy.deepcopy(network[k]) for k in ("IPAMConfig", "Links", "DriverOpts", "GwPriority")
             if network.get(k) is not None}
        if network.get("Aliases"):
            n["Aliases"] = [a for a in network["Aliases"] if a not in (old["Id"], old["Id"][:12])]
        networks[name] = n
    payload["NetworkingConfig"] = {"EndpointsConfig": networks}
    return payload


class Updater:
    def __init__(self, config, state_dir, *, docker=None):
        self.config = validate_config(config)
        self.root = Path(state_dir)
        self.docker = docker or Docker()

    def state(self, component):
        path = self.root / (component + ".json")
        return json.loads(path.read_text()) if path.exists() else {}

    def save(self, component, state):
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        dest = self.root / (component + ".json")
        tmp = dest.with_suffix(".new")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(state, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, dest)
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def server_version(self):
        # No redirects: the configured HTTPS server is the version authority.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(self.config["status_url"], timeout=20) as r:
            data = r.read(65537)
            if len(data) > 65536:
                raise Error("oversized server status response")
        value = json.loads(data)["Version"]
        version_tuple(value)
        return value

    def agent_health(self, version):
        # Portainer Agent uses a self-signed certificate. This exception is ONLY
        # for host-loopback health checks, never for the version authority URL.
        context = ssl._create_unverified_context()
        for _ in range(20):
            try:
                with urllib.request.urlopen("https://127.0.0.1:9001/ping", context=context, timeout=2) as r:
                    if r.status == 204 and r.headers.get("Portainer-Agent") == version:
                        return True
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(1)
        return False

    def clean_images(self, component, repository, current):
        state = self.state(component)
        keep = {current, state.get("previous_image")}
        remaining = []
        for ident in state.get("retired_images", []):
            if ident in keep:
                continue
            image = self.docker.image(ident)
            if image is None:
                continue
            tags = image.get("RepoTags") or []
            if any(not t.startswith(repository + ":") for t in tags):
                remaining.append(ident)
                log(component + ": skipped image with unrelated repository tags")
                continue
            try:
                self.docker.remove_image(ident)
                log(component + ": removed a recorded obsolete image")
            except Error:
                remaining.append(ident)
                log(component + ": retained obsolete image (still referenced or removal refused)")
        state["retired_images"] = remaining
        self.save(component, state)

    def remember_previous(self, component, old_image):
        state = self.state(component)
        old_previous = state.get("previous_image")
        retired = state.get("retired_images", [])
        if old_previous and old_previous != old_image:
            retired.append(old_previous)
        state.update(previous_image=old_image, retired_images=list(dict.fromkeys(retired)))
        self.save(component, state)

    def recover_agent(self):
        state = self.state("agent")
        txn = state.get("pending")
        if not txn:
            if self.docker.inspect(BACKUP, missing=True):
                raise Error("untracked agent rollback container; manual inspection required")
            return
        current = self.docker.inspect(AGENT, missing=True)
        backup = self.docker.inspect(BACKUP, missing=True)
        if backup and backup["Id"] != txn["old_id"]:
            raise Error("rollback container identity changed; refusing recovery")
        if txn["phase"] == "committed":
            if not current or current["Config"].get("Labels", {}).get(TXN_LABEL) != txn["token"]:
                raise Error("committed replacement identity changed")
            version = current["Config"]["Image"].split(":", 1)[1]
            if not current["State"]["Running"] or not self.agent_health(version):
                raise Error("committed agent unhealthy; recovery state retained")
            if backup:
                self.docker.remove(backup["Id"])
            state.pop("pending")
            self.save("agent", state)
            return
        if current and current["Id"] != txn["old_id"]:
            if not backup or current["Config"].get("Labels", {}).get(TXN_LABEL) != txn["token"]:
                raise Error("replacement is not owned by the interrupted transaction")
            if current["State"]["Running"]:
                self.docker.stop(current["Id"])
            self.docker.remove(current["Id"])
        if backup:
            self.docker.rename(backup["Id"], AGENT)
        restored = self.docker.inspect(AGENT)
        if restored["Id"] != txn["old_id"]:
            raise Error("original agent missing; recovery state retained")
        if not restored["State"]["Running"]:
            self.docker.start(restored["Id"])
        if not self.agent_health(txn["old_version"]):
            raise Error("original agent recovery health check failed")
        state.pop("pending")
        self.save("agent", state)
        raise Error("interrupted agent upgrade rolled back; retry on next run")

    def agent(self, *, check=False):
        if self.state("agent").get("pending"):
            if check:
                raise Error("pending agent transaction needs recovery")
            self.recover_agent()
        elif self.docker.inspect(BACKUP, missing=True):
            raise Error("untracked agent rollback container")
        old = self.docker.inspect(AGENT)
        image = old["Config"]["Image"]
        if not image.startswith("portainer/agent:"):
            raise Error("unexpected agent repository")
        current = image.split(":", 1)[1]
        version_tuple(current)
        target = self.server_version()
        old_image = self.docker.image(old["Image"])
        if not old_image or not isinstance(old_image.get("Config"), dict):
            raise Error("cannot establish the running agent image defaults")
        payload = agent_payload(old, target, uuid.uuid4().hex, old_image["Config"])
        if (len(payload["NetworkingConfig"]["EndpointsConfig"]) > 1
                and not self.docker.supports_multi_network()):
            raise Error("multi-network agents require Docker Engine 25+ (API 1.44+)")
        if not old["State"]["Running"] or not self.agent_health(current):
            raise Error("existing agent is stopped or unhealthy")
        if version_tuple(target) < version_tuple(current):
            raise Error("server is older than agent; refusing automatic downgrade")
        if target == current:
            log("agent: healthy and current (" + current + ")")
            if not check and self.state("agent"):
                self.clean_images("agent", "portainer/agent", old["Image"])
            return
        log("agent: " + current + " -> " + target + (" (check only)" if check else ""))
        if check:
            return
        self.docker.pull("portainer/agent:" + target)
        candidate_image = self.docker.image("portainer/agent:" + target)["Id"]
        # Recheck after a potentially slow pull; do not race an operator/controller.
        if self.docker.inspect(AGENT)["Id"] != old["Id"] or self.server_version() != target:
            raise Error("agent or server changed during pull")
        state = self.state("agent")
        state["pending"] = {"old_id": old["Id"], "old_image": old["Image"], "old_version": current,
                            "token": payload["Labels"][TXN_LABEL], "phase": "prepared"}
        self.save("agent", state)
        try:
            self.docker.stop(old["Id"])
            self.docker.rename(old["Id"], BACKUP)
            new_id = self.docker.create(AGENT, payload)
            self.docker.start(new_id)
            if not self.agent_health(target):
                raise Error("replacement agent failed its live version check")
            new = self.docker.inspect(AGENT)
            if new["Id"] != new_id or new["Image"] != candidate_image or not new["State"]["Running"]:
                raise Error("replacement changed during health verification")
        except Exception:
            self.recover_agent()
            raise
        self.remember_previous("agent", old["Image"])
        state = self.state("agent")
        state["pending"]["phase"] = "committed"
        self.save("agent", state)
        self.recover_agent()
        self.clean_images("agent", "portainer/agent", new["Image"])
        log("agent: upgraded and locally verified (" + target + ")")

    def run(self, *, check=False):
        # Recover routing before any HTTPS-dependent preflight. A pending Server
        # migration remains an unconditional manual-repair gate.
        if self.state("portainer").get("pending"):
            raise Error("Portainer upgrade needs manual repair/verification; no database downgrade attempted")
        if "core" in self.config and self.state("traefik").get("pending"):
            self.traefik(check=check)
        if self.state("agent").get("pending"):
            if check:
                raise Error("pending agent transaction needs recovery")
            self.recover_agent()
        self.portainer(check=check)
        self.traefik(check=check)
        self.agent(check=check)

    def compose(self, *args):
        t = self.config["core"]
        argv = ["docker", "compose", "--project-directory", t["directory"], "-p", t["project"]]
        for f in t["files"]:
            argv += ["-f", f]
        return command(argv + list(args), cwd=t["directory"])

    def core_hash(self, service):
        services = set(self.compose("config", "--services").split())
        if not services <= {"traefik", "portainer"} or service not in services:
            raise Error("core Compose project contains unexpected services")
        hashes = self.compose("config", "--hash", service).split()
        if len(hashes) != 2 or hashes[0] != service:
            raise Error("cannot establish core Compose configuration hash")
        return hashes[1]

    def core_container(self, service, *, missing=False) -> Any:
        c = self.docker.inspect("stacksmith_" + service, missing=missing)
        if c is None:
            return None
        labels = c["Config"].get("Labels") or {}
        t = self.config["core"]
        if (labels.get("com.docker.compose.project") != t["project"]
                or labels.get("com.docker.compose.service") != service
                or labels.get("com.docker.compose.project.working_dir") != t["directory"]
                or labels.get("com.docker.compose.project.config_files") != ",".join(t["files"])):
            raise Error(service + ": Compose ownership does not match configuration")
        ref = "traefik:latest" if service == "traefik" else "portainer/portainer-ce:latest"
        if c["Config"]["Image"] != ref:
            raise Error(service + ": automation expects the existing moving latest policy")
        if self.core_hash(service) != labels.get("com.docker.compose.config-hash"):
            raise Error(service + ": configuration changed; reconcile it manually before image updates")
        return c

    def wait_core(self, image, service="traefik"):
        for _ in range(20):
            try:
                c = self.docker.inspect("stacksmith_" + service)
                if c["State"]["Running"] and c["Image"] == image:
                    self.server_version()  # Exercises HTTPS routing and the Portainer application.
                    return True
            except (Error, OSError, ValueError, urllib.error.URLError):
                pass
            time.sleep(2)
        return False

    def rollback_traefik(self, state):
        txn = state["pending"]
        # Compose can remove the old container before failing to create its
        # replacement. Validate saved ownership/configuration even when absent.
        c = self.core_container("traefik", missing=True)
        if self.core_hash("traefik") != txn["config_hash"]:
            raise Error("Traefik configuration changed; refusing automatic rollback")
        if c and c["Image"] not in (txn["old_image"], txn["new_image"]):
            raise Error("Traefik image changed externally; refusing automatic rollback")
        command(["docker", "image", "tag", txn["old_image"], "traefik:latest"])
        self.compose("up", "-d", "--no-deps", "--pull", "never", "traefik")
        if not self.wait_core(txn["old_image"]):
            raise Error("Traefik rollback failed; recovery state retained")
        state.pop("pending")
        self.save("traefik", state)
        raise Error("Traefik upgrade rolled back; retry on next run")

    def portainer(self, *, check=False):
        if self.config.get("core", {}).get("portainer_without_backup", False):
            self.core_update("portainer", check=check)

    def traefik(self, *, check=False):
        if "core" in self.config:
            self.core_update("traefik", check=check)

    def core_update(self, service, *, check=False):
        state = self.state(service)
        if state.get("pending"):
            if service == "portainer":
                raise Error("Portainer upgrade needs manual repair/verification; no database downgrade attempted")
            if check:
                raise Error("pending Traefik transaction needs recovery")
            self.rollback_traefik(state)
        old = self.core_container(service)
        if not old["State"]["Running"]:
            raise Error(service + ": intentionally stopped or unhealthy")
        self.server_version()
        if check:
            log(service + ": ownership, configuration and HTTPS route verified (check only)")
            return
        self.compose("pull", "--policy", "always", service)
        ref = old["Config"]["Image"]
        repository = ref.rsplit(":", 1)[0]
        candidate = self.docker.image(ref)["Id"]
        if candidate == old["Image"]:
            log(service + ": healthy; image unchanged")
            if state:
                self.clean_images(service, repository, candidate)
            return
        if self.core_container(service)["Id"] != old["Id"]:
            raise Error(service + ": changed during pull")
        state["pending"] = {"old_image": old["Image"], "new_image": candidate,
                            "config_hash": old["Config"]["Labels"]["com.docker.compose.config-hash"]}
        self.save(service, state)
        try:
            self.compose("up", "-d", "--no-deps", "--pull", "never", service)
            if not self.wait_core(candidate, service):
                raise Error(service + ": replacement failed HTTPS health verification")
        except Exception:
            if service == "traefik":
                self.rollback_traefik(state)
            state["pending"]["phase"] = "failed"
            self.save(service, state)
            raise Error("Portainer upgrade failed; stopped for manual repair, no database downgrade attempted")
        self.remember_previous(service, old["Image"])
        state = self.state(service)
        state.pop("pending")
        self.save(service, state)
        self.clean_images(service, repository, candidate)
        log(service + ": upgraded; HTTPS Portainer route verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="/etc/stacksmith-maintenance.json")
    parser.add_argument("--state-dir", default="/var/lib/stacksmith-maintenance")
    parser.add_argument("--check", action="store_true", help="preflight without pulls or Docker mutations")
    args = parser.parse_args()
    def interrupted(signum, frame):
        raise Error("maintenance interrupted; recovery journal retained if needed")
    signal.signal(signal.SIGTERM, interrupted)
    os.umask(0o077)
    config_path = Path(args.config)
    if os.geteuid() != 0 or config_path.stat().st_uid != 0 or config_path.stat().st_mode & 0o022:
        raise Error("run as root with a root-owned, non-group/world-writable config")
    updater = Updater(json.loads(config_path.read_text()), Path(args.state_dir))
    updater.root.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (updater.root / "lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Error("another maintenance run is active")
        updater.run(check=args.check)
    log("maintenance: completed" + (" (check only)" if args.check else ""))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never dump inspect/configuration data or subprocess output into journals.
        log("maintenance: FAILED: " + (str(exc) if isinstance(exc, Error) else type(exc).__name__))
        sys.exit(1)
