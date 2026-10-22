"""Deterministic tests; no host Docker daemon or production data is accessed."""
import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
from typing import Any

SPEC = importlib.util.spec_from_file_location("maintain", pathlib.Path(__file__).with_name("maintain.py"))
assert SPEC is not None and SPEC.loader is not None
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def container(name="portainer_agent", image="portainer/agent:2.45.2", ident="old"):
    return {"Id": ident, "Name": "/" + name, "Image": "sha256:" + ident,
            "State": {"Running": True},
            "Config": {"Image": image, "Hostname": ident[:12], "Env": ["PATH=/bin"], "Labels": {}},
            "HostConfig": {"NetworkMode": "bridge", "RestartPolicy": {"Name": "always"},
                           "PortBindings": {"9001/tcp": [{"HostIp": "127.0.0.1", "HostPort": "9001"}]},
                           "Binds": ["/var/run/docker.sock:/var/run/docker.sock"]},
            "Mounts": [{"Type": "bind", "Source": "/var/run/docker.sock", "Destination": "/var/run/docker.sock"}],
            "NetworkSettings": {"Networks": {"bridge": {"Aliases": None},
                                            "stacksmith": {"Aliases": ["portainer_agent", ident[:12]],
                                                           "IPAMConfig": None, "IPAddress": "172.20.0.8"}}}}


class FakeDocker:
    def __init__(self):
        self.containers = {"portainer_agent": container()}
        self.events = []
        self.fail: str | None = None
        self.images: dict[str, dict[str, Any]] = {"sha256:old": {"RepoTags": ["portainer/agent:2.45.2"]}}

    def event(self, op, *args):
        self.events.append((op, *args))
        if self.fail == op:
            self.fail = None
            raise m.Error("injected " + op)

    def inspect(self, name, missing=False) -> Any:
        if name in self.containers:
            return copy.deepcopy(self.containers[name])
        for c in self.containers.values():
            if c["Id"] == name:
                return copy.deepcopy(c)
        if missing:
            return None
        raise m.Error("container missing")

    def supports_multi_network(self):
        return True

    def pull(self, image):
        self.event("pull", image)
        self.images[image] = {"Id": "sha256:new", "RepoTags": [image]}

    def image(self, image):
        return self.images[image]

    def stop(self, name):
        self.event("stop", name)
        self._find(name)["State"]["Running"] = False

    def _find(self, name):
        for c in self.containers.values():
            if c["Id"] == name or c["Name"] == "/" + name:
                return c
        raise m.Error("not found")

    def rename(self, name, new):
        self.event("rename", name, new)
        c = self._find(name)
        oldname = c["Name"][1:]
        c["Name"] = "/" + new
        self.containers[new] = self.containers.pop(oldname)

    def create(self, name, payload):
        self.event("create", name)
        c = container(name, payload["Image"], "new")
        c["Config"] = {k: copy.deepcopy(v) for k, v in payload.items()
                       if k not in ("HostConfig", "NetworkingConfig")}
        c["HostConfig"] = copy.deepcopy(payload["HostConfig"])
        c["NetworkSettings"]["Networks"] = copy.deepcopy(payload["NetworkingConfig"]["EndpointsConfig"])
        c["State"]["Running"] = False
        self.containers[name] = c
        return "new"

    def start(self, name):
        self.event("start", name)
        self._find(name)["State"]["Running"] = True

    def remove(self, name):
        self.event("remove", name)
        c = self._find(name)
        del self.containers[c["Name"][1:]]

    def remove_image(self, ident):
        self.event("remove_image", ident)
        del self.images[ident]


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = FakeDocker()
        self.u = m.Updater({"status_url": "https://management.example.com/api/status"},
                           pathlib.Path(self.tmp.name), docker=self.d)
        self.ping = patch.object(self.u, "agent_health", return_value=True).start()
        self.version = patch.object(self.u, "server_version", return_value="2.45.3").start()
        self.addCleanup(patch.stopall)

    def test_upgrade_preserves_bindings_networks_and_environment(self):
        old = self.d.inspect("portainer_agent")
        self.u.agent()
        now = self.d.inspect("portainer_agent")
        self.assertEqual(now["Config"]["Image"], "portainer/agent:2.45.3")
        self.assertEqual(now["HostConfig"], old["HostConfig"])
        self.assertEqual(now["Config"]["Env"], old["Config"]["Env"])
        self.assertEqual(set(now["NetworkSettings"]["Networks"]), {"bridge", "stacksmith"})
        self.assertNotIn("IPAddress", now["NetworkSettings"]["Networks"]["stacksmith"])
        self.assertNotIn("old", now["NetworkSettings"]["Networks"]["stacksmith"]["Aliases"])
        self.assertFalse(self.d.inspect(m.BACKUP, missing=True))
        self.assertEqual(self.u.state("agent")["previous_image"], "sha256:old")

    def test_same_version_is_read_only(self):
        self.version.return_value = "2.45.2"
        self.u.agent()
        self.assertEqual(self.d.events, [])

    def test_does_not_downgrade(self):
        self.version.return_value = "2.45.1"
        with self.assertRaises(m.Error):
            self.u.agent()
        self.assertEqual(self.d.events, [])

    def test_check_mode_never_pulls_or_changes_container(self):
        self.u.agent(check=True)
        self.assertEqual(self.d.events, [])

    def test_stopped_agent_is_not_started_implicitly(self):
        self.d.containers["portainer_agent"]["State"]["Running"] = False
        with self.assertRaises(m.Error):
            self.u.agent()
        self.assertEqual(self.d.events, [])

    def test_rejects_compose_managed_agent(self):
        self.d.containers["portainer_agent"]["Config"]["Labels"]["com.docker.compose.project"] = "external"
        with self.assertRaises(m.Error):
            self.u.agent()
        self.assertEqual(self.d.events, [])

    def test_anonymous_volume_is_rejected_without_replacement(self):
        self.d.containers["portainer_agent"]["Mounts"].append(
            {"Type": "volume", "Name": "opaque-volume", "Destination": "/data"})
        with self.assertRaises(m.Error):
            self.u.agent()
        self.assertEqual(self.d.events, [])

    def test_declared_volume_backed_by_bind_is_supported(self):
        self.d.containers["portainer_agent"]["Config"]["Volumes"] = {"/var/run/docker.sock": {}}
        self.u.agent()
        self.assertEqual(self.d.inspect("portainer_agent")["Config"]["Image"], "portainer/agent:2.45.3")

    def test_unbacked_volume_declaration_is_rejected(self):
        self.d.containers["portainer_agent"]["Config"]["Volumes"] = {"/unbacked": {}}
        with self.assertRaises(m.Error):
            self.u.agent()
        self.assertEqual(self.d.events, [])

    def test_old_engine_is_rejected_before_stopping_multi_network_agent(self):
        with patch.object(self.d, "supports_multi_network", return_value=False):
            with self.assertRaisesRegex(m.Error, "API 1.44"):
                self.u.agent()
        self.assertEqual(self.d.events, [])

    def test_failed_create_restores_old_identity(self):
        self.d.fail = "create"
        with self.assertRaises(m.Error):
            self.u.agent()
        self.assertEqual(self.d.inspect("portainer_agent")["Id"], "old")
        self.assertTrue(self.d.inspect("portainer_agent")["State"]["Running"])

    def test_failed_health_rolls_back(self):
        self.ping.side_effect = [True, False, True]
        with self.assertRaises(m.Error):
            self.u.agent()
        self.assertEqual(self.d.inspect("portainer_agent")["Id"], "old")
        self.assertTrue(self.d.inspect("portainer_agent")["State"]["Running"])

    def test_interrupted_transaction_is_rolled_back_before_retry(self):
        old = self.d.inspect("portainer_agent")
        self.u.save("agent", {"pending": {"old_id": old["Id"], "old_image": old["Image"],
                                         "old_version": "2.45.2", "token": "txn", "phase": "prepared"}})
        self.d.stop("old")
        self.d.rename("old", m.BACKUP)
        self.d.create("portainer_agent", m.agent_payload(old, "2.45.3", "txn"))
        with self.assertRaises(m.Error):
            self.u.agent()
        self.assertEqual(self.d.inspect("portainer_agent")["Id"], "old")
        self.assertNotIn("pending", self.u.state("agent"))

    def test_recovery_refuses_foreign_replacement(self):
        self.u.save("agent", {"pending": {"old_id": "old", "old_image": "sha256:old",
                                         "old_version": "2.45.2", "token": "txn", "phase": "prepared"}})
        self.d.rename("old", m.BACKUP)
        self.d.containers["portainer_agent"] = container(ident="foreign")
        with self.assertRaises(m.Error):
            self.u.agent()
        self.assertEqual(self.d.inspect("portainer_agent")["Id"], "foreign")
        self.assertFalse(any(e[0] == "remove" for e in self.d.events))

    def test_committed_interruption_only_cleans_backup(self):
        self.u.agent()
        self.d.containers[m.BACKUP] = container(m.BACKUP)
        self.d.containers[m.BACKUP]["State"]["Running"] = False
        self.u.save("agent", {"pending": {"old_id": "old", "old_image": "sha256:old",
                                         "old_version": "2.45.2", "token": self.d.inspect("portainer_agent")["Config"]["Labels"][m.TXN_LABEL],
                                         "phase": "committed"}, "previous_image": "sha256:old"})
        self.u.agent()
        self.assertEqual(self.d.inspect("portainer_agent")["Id"], "new")
        self.assertIsNone(self.d.inspect(m.BACKUP, missing=True))

    def test_cleanup_never_deletes_other_repository_tags(self):
        self.u.save("agent", {"retired_images": ["sha256:foreign"], "previous_image": "sha256:old"})
        self.d.images["sha256:foreign"] = {"RepoTags": ["other/app:latest"]}
        self.u.clean_images("agent", "portainer/agent", "sha256:new")
        self.assertIn("sha256:foreign", self.d.images)

    def test_cleanup_preserves_current_and_previous_and_removes_owned_old_image(self):
        self.u.save("agent", {"retired_images": ["sha256:old", "sha256:ancient", "sha256:new"],
                              "previous_image": "sha256:old"})
        self.d.images["sha256:ancient"] = {"RepoTags": ["portainer/agent:2.44.0"]}
        self.u.clean_images("agent", "portainer/agent", "sha256:new")
        self.assertNotIn("sha256:ancient", self.d.images)
        self.assertIn("sha256:old", self.d.images)
        self.assertNotIn(("remove_image", "sha256:new"), self.d.events)


class TraefikTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = FakeDocker()
        c = container("stacksmith_traefik", "traefik:latest", "traefik-old")
        c["Config"]["Labels"] = {
            "com.docker.compose.project": "stacksmith",
            "com.docker.compose.service": "traefik",
            "com.docker.compose.project.working_dir": "/srv/stacksmith",
            "com.docker.compose.project.config_files": "/srv/stacksmith/docker-compose.yml,/srv/stacksmith/traefik/docker-compose.yml",
            "com.docker.compose.config-hash": "expected-hash"}
        self.d.containers["stacksmith_traefik"] = c
        self.d.images["traefik:latest"] = {"Id": "sha256:traefik-new"}
        self.u = m.Updater({"status_url": "https://management.example.com/api/status",
                            "core": {"directory": "/srv/stacksmith", "project": "stacksmith",
                                        "files": ["/srv/stacksmith/docker-compose.yml", "/srv/stacksmith/traefik/docker-compose.yml"]}},
                           pathlib.Path(self.tmp.name), docker=self.d)
        self.calls = []
        self.fail_up = False
        self.remove_before_failure = False
        self.extra_service = False
        self.hash = "expected-hash"
        def compose(*args):
            self.calls.append(args)
            if args == ("config", "--services"):
                return "portainer\ntraefik\n" + ("unrelated\n" if self.extra_service else "")
            if args == ("config", "--hash", "traefik"):
                return "traefik " + self.hash
            if args[0] == "up":
                if self.fail_up:
                    self.fail_up = False
                    if self.remove_before_failure:
                        del self.d.containers["stacksmith_traefik"]
                    raise m.Error("injected up failure")
                if "stacksmith_traefik" not in self.d.containers:
                    self.d.containers["stacksmith_traefik"] = copy.deepcopy(c)
                self.d.containers["stacksmith_traefik"]["Image"] = self.d.images["traefik:latest"]["Id"]
            return ""
        patch.object(self.u, "compose", side_effect=compose).start()
        patch.object(self.u, "server_version", return_value="2.45.3").start()
        def cmd(args, **kwargs):
            if args[:3] == ["docker", "image", "tag"]:
                self.d.images["traefik:latest"] = {"Id": args[3]}
            return ""
        patch.object(m, "command", side_effect=cmd).start()
        patch.object(m.time, "sleep").start()
        self.addCleanup(patch.stopall)

    def test_upgrades_only_named_service_with_no_dependencies_or_pulls_during_recreate(self):
        self.u.traefik()
        self.assertIn(("pull", "--policy", "always", "traefik"), self.calls)
        self.assertIn(("up", "-d", "--no-deps", "--pull", "never", "traefik"), self.calls)
        self.assertNotIn("pending", self.u.state("traefik"))
        self.assertEqual(self.u.state("traefik")["previous_image"], "sha256:traefik-old")
        self.assertEqual(self.d.inspect("portainer_agent")["Id"], "old")

    def test_check_has_no_pull_or_recreate(self):
        self.u.traefik(check=True)
        self.assertFalse(any(c[0] in ("pull", "up") for c in self.calls))

    def test_no_new_image_does_not_recreate(self):
        self.d.images["traefik:latest"]["Id"] = "sha256:traefik-old"
        self.u.traefik()
        self.assertFalse(any(c[0] == "up" for c in self.calls))

    def test_changed_configuration_stops_before_pull(self):
        self.hash = "changed-hash"
        with self.assertRaises(m.Error):
            self.u.traefik()
        self.assertFalse(any(c[0] == "pull" for c in self.calls))

    def test_unexpected_workload_in_core_project_stops_before_pull(self):
        self.extra_service = True
        with self.assertRaises(m.Error):
            self.u.traefik()
        self.assertFalse(any(c[0] == "pull" for c in self.calls))

    def test_failed_recreate_restores_original_image_through_canonical_compose(self):
        self.fail_up = True
        with self.assertRaises(m.Error):
            self.u.traefik()
        self.assertEqual(self.d.inspect("stacksmith_traefik")["Image"], "sha256:traefik-old")
        self.assertNotIn("pending", self.u.state("traefik"))

    def test_failed_route_health_rolls_back(self):
        with patch.object(self.u, "wait_core", side_effect=[False, True]):
            with self.assertRaises(m.Error):
                self.u.traefik()
        self.assertEqual(self.d.inspect("stacksmith_traefik")["Image"], "sha256:traefik-old")

    def test_failed_recreate_after_old_container_removal_still_restores_service(self):
        self.fail_up = self.remove_before_failure = True
        with self.assertRaises(m.Error):
            self.u.traefik()
        self.assertEqual(self.d.inspect("stacksmith_traefik")["Image"], "sha256:traefik-old")
        self.assertNotIn("pending", self.u.state("traefik"))

    def test_pending_transaction_is_recovered_before_new_pull(self):
        self.u.save("traefik", {"pending": {"old_image": "sha256:traefik-old", "new_image": "sha256:traefik-new", "config_hash": "expected-hash"}})
        self.d.containers["stacksmith_traefik"]["Image"] = "sha256:traefik-new"
        with self.assertRaises(m.Error):
            self.u.traefik()
        self.assertEqual(self.d.inspect("stacksmith_traefik")["Image"], "sha256:traefik-old")
        self.assertFalse(any(c[0] == "pull" for c in self.calls))

    def test_run_recovers_routing_before_portainer_preflight(self):
        self.u.config["core"]["portainer_without_backup"] = True
        self.u.save("traefik", {"pending": {"old_image": "sha256:traefik-old",
                    "new_image": "sha256:traefik-new", "config_hash": "expected-hash"}})
        del self.d.containers["stacksmith_traefik"]
        def version():
            if "stacksmith_traefik" not in self.d.containers:
                raise m.Error("route unavailable")
            return "2.45.3"
        with patch.object(self.u, "server_version", side_effect=version):
            with self.assertRaisesRegex(m.Error, "Traefik upgrade rolled back"):
                self.u.run()
        self.assertEqual(self.d.inspect("stacksmith_traefik")["Image"], "sha256:traefik-old")
        self.assertFalse(any(c[0] == "pull" for c in self.calls))
        self.assertNotIn("pending", self.u.state("traefik"))

    def test_run_preserves_portainer_latch_before_any_recovery(self):
        self.u.save("portainer", {"pending": {"phase": "failed"}})
        self.u.save("traefik", {"pending": {"old_image": "sha256:traefik-old"}})
        with self.assertRaisesRegex(m.Error, "manual repair"):
            self.u.run()
        self.assertEqual(self.calls, [])

    def test_check_does_not_recover_pending_routing(self):
        self.u.save("traefik", {"pending": {"old_image": "sha256:traefik-old"}})
        with self.assertRaisesRegex(m.Error, "needs recovery"):
            self.u.run(check=True)
        self.assertEqual(self.calls, [])

    def test_foreign_image_is_not_rolled_back(self):
        self.u.save("traefik", {"pending": {"old_image": "sha256:traefik-old", "new_image": "sha256:traefik-new", "config_hash": "expected-hash"}})
        self.d.containers["stacksmith_traefik"]["Image"] = "sha256:foreign"
        with self.assertRaises(m.Error):
            self.u.traefik()
        self.assertFalse(any(c[0] == "up" for c in self.calls))


class PortainerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = FakeDocker()
        self.paths = ["/srv/stacksmith/docker-compose.yml", "/srv/stacksmith/traefik/docker-compose.yml"]
        old = container("stacksmith_portainer", "portainer/portainer-ce:latest", "server-old")
        old["Config"]["Labels"] = {"com.docker.compose.project": "stacksmith",
                                   "com.docker.compose.service": "portainer",
                                   "com.docker.compose.project.working_dir": "/srv/stacksmith",
                                   "com.docker.compose.project.config_files": ",".join(self.paths),
                                   "com.docker.compose.config-hash": "server-hash"}
        self.d.containers["stacksmith_portainer"] = old
        self.d.images["portainer/portainer-ce:latest"] = {"Id": "sha256:server-new"}
        self.u = m.Updater({"status_url": "https://management.example.com/api/status",
                            "core": {"directory": "/srv/stacksmith", "project": "stacksmith",
                                     "files": self.paths, "portainer_without_backup": True}},
                           pathlib.Path(self.tmp.name), docker=self.d)
        self.calls = []
        self.fail_up = False
        def compose(*args):
            self.calls.append(args)
            if args == ("config", "--services"):
                return "portainer\ntraefik"
            if args == ("config", "--hash", "portainer"):
                return "portainer server-hash"
            if args[0] == "up":
                if self.fail_up:
                    del self.d.containers["stacksmith_portainer"]
                    raise m.Error("failed after old container removal")
                self.d.containers["stacksmith_portainer"]["Image"] = self.d.images["portainer/portainer-ce:latest"]["Id"]
            return ""
        patch.object(self.u, "compose", side_effect=compose).start()
        patch.object(self.u, "server_version", return_value="2.45.3").start()
        self.cmd = patch.object(m, "command").start()
        patch.object(m.time, "sleep").start()
        self.addCleanup(patch.stopall)

    def test_server_updates_only_with_explicit_risk_opt_in(self):
        self.u.config["core"].pop("portainer_without_backup")
        self.u.portainer()
        self.assertEqual(self.calls, [])

    def test_server_upgrade_preserves_existing_compose_ownership_without_volume_operations(self):
        self.u.portainer()
        self.assertIn(("up", "-d", "--no-deps", "--pull", "never", "portainer"), self.calls)
        self.assertEqual(self.d.inspect("stacksmith_portainer")["Config"]["Labels"]["com.docker.compose.project"], "stacksmith")
        self.assertEqual(self.u.state("portainer")["previous_image"], "sha256:server-old")
        self.assertNotIn("pending", self.u.state("portainer"))
        self.assertEqual(self.d.events, [])

    def test_failed_upgrade_latches_without_image_or_database_downgrade(self):
        self.fail_up = True
        with self.assertRaises(m.Error):
            self.u.portainer()
        self.assertEqual(self.u.state("portainer")["pending"]["phase"], "failed")
        self.cmd.assert_not_called()
        calls = list(self.calls)
        with self.assertRaises(m.Error):
            self.u.portainer()
        self.assertEqual(self.calls, calls)

    def test_failed_https_health_does_not_downgrade_server(self):
        with patch.object(self.u, "wait_core", return_value=False):
            with self.assertRaises(m.Error):
                self.u.portainer()
        self.assertEqual(self.d.inspect("stacksmith_portainer")["Image"], "sha256:server-new")
        self.assertIn("pending", self.u.state("portainer"))
        self.cmd.assert_not_called()

    def test_interrupted_upgrade_requires_operator_verification(self):
        self.u.save("portainer", {"pending": {"old_image": "sha256:server-old", "new_image": "sha256:server-new"}})
        with self.assertRaises(m.Error):
            self.u.portainer()
        self.assertEqual(self.calls, [])

    def test_unchanged_server_image_is_not_recreated(self):
        self.d.images["portainer/portainer-ce:latest"]["Id"] = "sha256:server-old"
        self.u.portainer()
        self.assertFalse(any(c[0] == "up" for c in self.calls))

    def test_check_does_not_pull_or_recreate_server(self):
        self.u.portainer(check=True)
        self.assertFalse(any(c[0] in ("pull", "up") for c in self.calls))


class ValidationTests(unittest.TestCase):
    def test_docker_api_multi_network_requirement(self):
        docker = m.Docker()
        for version, expected in [("1.43", False), ("1.44", True), ("1.56", True)]:
            with patch.object(docker, "request", return_value={"ApiVersion": version}):
                self.assertEqual(docker.supports_multi_network(), expected)

    def test_version_rejects_shell_fragments_and_prereleases(self):
        for version in ["2.45.3;id", "latest", "2.45.3-rc1", "v2.45.3", "2.45.3/../x"]:
            with self.assertRaises(m.Error):
                m.version_tuple(version)
        self.assertEqual(m.version_tuple("2.45.3"), (2, 45, 3))

    def test_config_rejects_http_credentials_and_unknown_keys(self):
        for config in [{"status_url": "http://example.com/api/status"},
                       {"status_url": "https://user:password@example.com/api/status"},
                       {"status_url": "https://example.com/api/status", "arbitrary": "x"}]:
            with self.assertRaises(m.Error):
                m.validate_config(config)

    def test_payload_does_not_mutate_original_inspection(self):
        old = container()
        frozen = copy.deepcopy(old)
        m.agent_payload(old, "2.45.3", "test")
        self.assertEqual(old, frozen)


if __name__ == "__main__":
    unittest.main()
