from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

from tests.support.app_harness import AppTestHarness
from tests.support.fake_home import seed_divergent_source_fixture, seed_managed_linked_fixture, seed_skill_package


class HttpApiTests(unittest.TestCase):
    def test_empty_fixture_returns_skills_settings_and_health(self) -> None:
        with AppTestHarness() as harness:
            health = harness.get_json("/api/health")
            skills = harness.get_json("/api/skills")
            settings = harness.get_json("/api/settings")

            self.assertTrue(health["ok"])
            self.assertEqual(skills["summary"], {"managed": 0, "unmanaged": 0})
            self.assertEqual(skills["rows"], [])
            self.assertEqual(settings["storage"]["skillsStorePath"], str(harness.spec.skills_store_root))
            self.assertEqual(
                settings["storage"]["marketplaceCachePath"],
                str(harness.spec.xdg_data_home / "skill-manager" / "marketplace"),
            )
            self.assertEqual(
                settings["storage"]["settingsPath"],
                str(harness.spec.xdg_config_home / "skill-manager" / "settings.json"),
            )
            self.assertEqual(len(settings["harnesses"]), 7)
            trae = next(item for item in settings["harnesses"] if item["harness"] == "trae")
            self.assertEqual(trae["label"], "Trae CN")
            self.assertEqual(trae["managedLocation"], str(harness.spec.home / ".trae-cn" / "skills"))
            openclaw = next(item for item in settings["harnesses"] if item["harness"] == "openclaw")
            self.assertTrue(openclaw["installed"])
            self.assertTrue(openclaw["supportEnabled"])
            self.assertEqual(openclaw["managedLocation"], str(harness.spec.home / ".openclaw" / "skills"))
            self.assertNotIn("discoveryMode", openclaw)
            self.assertNotIn("centralStore", settings)
            self.assertNotIn("topology", settings)

    def test_health_skills_and_settings_work_without_openclaw_state(self) -> None:
        with AppTestHarness(seed_openclaw=False) as harness:
            health = harness.get_json("/api/health")
            skills = harness.get_json("/api/skills")
            settings = harness.get_json("/api/settings")

            self.assertTrue(health["ok"])
            self.assertEqual(skills["summary"], {"managed": 0, "unmanaged": 0})
            self.assertEqual(skills["rows"], [])
            openclaw = next(item for item in settings["harnesses"] if item["harness"] == "openclaw")
            self.assertFalse(openclaw["installed"])
            self.assertTrue(openclaw["supportEnabled"])
            self.assertEqual(openclaw["managedLocation"], str(harness.spec.home / ".openclaw" / "skills"))
            self.assertNotIn("openclaw", [column["harness"] for column in skills["harnessColumns"]])

    def test_skills_api_only_exposes_detected_installed_harnesses(self) -> None:
        with AppTestHarness(seed_openclaw=False) as harness:
            for cli in ("cursor-agent", "opencode", "hermes", "trae"):
                stub = harness.spec.cli_path(cli)
                if stub.exists():
                    stub.unlink()
            harness.container.skills_read_models.invalidate()

            skills = harness.get_json("/api/skills")
            settings = harness.get_json("/api/settings")
            visible = {column["harness"] for column in skills["harnessColumns"]}
            installed = {
                item["harness"]
                for item in settings["harnesses"]
                if item["installed"] and item["supportEnabled"]
            }

            self.assertEqual(visible, installed)
            self.assertTrue(all(column["installed"] for column in skills["harnessColumns"]))

    def test_settings_support_toggle_hides_disabled_harness_from_skills_inventory(self) -> None:
        with AppTestHarness(mixed=True) as harness:
            settings = harness.get_json("/api/settings")
            codex = next(item for item in settings["harnesses"] if item["harness"] == "codex")

            self.assertTrue(codex["supportEnabled"])

            harness.put_json("/api/settings/harnesses/codex/support", {"enabled": False})

            updated_settings = harness.get_json("/api/settings")
            updated_codex = next(item for item in updated_settings["harnesses"] if item["harness"] == "codex")
            skills = harness.get_json("/api/skills")

            self.assertFalse(updated_codex["supportEnabled"])
            self.assertNotIn("codex", [column["harness"] for column in skills["harnessColumns"]])

    def test_settings_support_toggle_hides_and_restores_trae_from_skills_inventory(self) -> None:
        def _seed(spec) -> None:
            seed_skill_package(spec.trae_root, "trae-audit", "Trae Audit")

        with AppTestHarness(fixture_factory=_seed) as harness:
            before = harness.get_json("/api/skills")
            self.assertIn("trae", [column["harness"] for column in before["harnessColumns"]])

            harness.put_json("/api/settings/harnesses/trae/support", {"enabled": False})

            settings = harness.get_json("/api/settings")
            disabled = harness.get_json("/api/skills")
            trae = next(item for item in settings["harnesses"] if item["harness"] == "trae")

            self.assertFalse(trae["supportEnabled"])
            self.assertNotIn("trae", [column["harness"] for column in disabled["harnessColumns"]])

            harness.put_json("/api/settings/harnesses/trae/support", {"enabled": True})

            restored = harness.get_json("/api/skills")
            self.assertIn("trae", [column["harness"] for column in restored["harnessColumns"]])

    def test_mixed_fixture_returns_skills_page_and_detail(self) -> None:
        with AppTestHarness(mixed=True) as harness:
            skills = harness.get_json("/api/skills")

            shared_audit = next(row for row in skills["rows"] if row["name"] == "Shared Audit")
            trace_lens = next(row for row in skills["rows"] if row["name"] == "Trace Lens")
            detail = harness.get_json(f"/api/skills/{shared_audit['skillRef']}")
            source_status = harness.get_json(f"/api/skills/{shared_audit['skillRef']}/source-status")

            self.assertEqual(skills["summary"], {"managed": 1, "unmanaged": 2})
            self.assertEqual(shared_audit["displayStatus"], "Managed")
            self.assertEqual(shared_audit["actions"], {"canManage": False, "canStopManaging": False, "canDelete": True})
            self.assertEqual(trace_lens["displayStatus"], "Unmanaged")
            self.assertEqual(trace_lens["actions"], {"canManage": True, "canStopManaging": False, "canDelete": False})
            self.assertEqual(detail["displayStatus"], "Managed")
            self.assertEqual(
                [cell["label"] for cell in detail["harnessCells"]],
                ["Codex", "Claude", "Cursor", "OpenCode", "Trae CN", "Hermes", "OpenClaw"],
            )
            self.assertNotIn("updateStatus", detail["actions"])
            self.assertEqual(source_status["updateStatus"], "no_update_available")
            self.assertEqual(detail["actions"]["stopManagingStatus"], "disabled_no_enabled")
            self.assertEqual(detail["actions"]["stopManagingHarnessLabels"], [])
            self.assertTrue(detail["actions"]["canDelete"])
            self.assertEqual(detail["actions"]["deleteHarnessLabels"], [])
            self.assertIn("Shared package fixture.", detail["documentMarkdown"])
            self.assertNotIn("statusMessage", detail)
            self.assertNotIn("source", detail)
            self.assertNotIn("advanced", detail)
            self.assertEqual(detail["sourceLinks"], {
                "repoLabel": "example-org/shared-audit",
                "repoUrl": "https://github.com/example-org/shared-audit",
                "folderUrl": None,
            })

    def test_managed_detail_returns_shared_store_location_before_tool_links(self) -> None:
        with AppTestHarness(fixture_factory=seed_managed_linked_fixture) as harness:
            skills = harness.get_json("/api/skills")
            shared_audit = next(row for row in skills["rows"] if row["name"] == "Shared Audit")
            detail = harness.get_json(f"/api/skills/{shared_audit['skillRef']}")

            self.assertEqual([location["label"] for location in detail["locations"]], ["Shared Store", "Codex", "OpenClaw", "OpenCode"])
            self.assertEqual(detail["actions"]["stopManagingStatus"], "available")
            self.assertEqual(detail["actions"]["stopManagingHarnessLabels"], ["Codex"])
            self.assertEqual(detail["actions"]["deleteHarnessLabels"], ["Codex"])

    def test_divergent_source_fixture_returns_separate_found_rows(self) -> None:
        with AppTestHarness(fixture_factory=seed_divergent_source_fixture) as harness:
            skills = harness.get_json("/api/skills")
            policy_rows = [row for row in skills["rows"] if row["name"] == "Policy Kit"]

            self.assertEqual(len(policy_rows), 2)
            self.assertTrue(all(row["displayStatus"] == "Unmanaged" for row in policy_rows))

    def test_unknown_skill_detail_returns_404_payload(self) -> None:
        with AppTestHarness() as harness:
            payload = harness.get_json("/api/skills/missing-entry", expected_status=404)
            self.assertIn("unknown skill ref", payload["error"])

    def test_frontend_routes_return_spa_shell_when_dist_is_present(self) -> None:
        with TemporaryDirectory(prefix="skill-manager-dist-") as tempdir:
            dist = Path(tempdir)
            (dist / "index.html").write_text("<!doctype html><html><body><div id='root'>skill-manager</div></body></html>", encoding="utf-8")

            with AppTestHarness(frontend_dist=dist) as harness:
                for path in ("/", "/skills", "/skills/managed", "/skills/unmanaged", "/marketplace", "/settings"):
                    with urlopen(f"{harness.base_url}{path}") as response:
                        body = response.read().decode("utf-8")
                    self.assertEqual(response.status, 200)
                    self.assertIn("<div id='root'>skill-manager</div>", body)

    def test_settings_expose_default_context_window(self) -> None:
        with AppTestHarness() as harness:
            settings = harness.get_json("/api/settings")
        self.assertEqual(settings["contextWindowTokens"], 128000)

    def test_put_context_window_persists_value(self) -> None:
        with AppTestHarness() as harness:
            response = harness.put_json("/api/settings/context-window", {"contextWindowTokens": 64000})
            self.assertEqual(response, {"ok": True, "contextWindowTokens": 64000})

            settings = harness.get_json("/api/settings")
            self.assertEqual(settings["contextWindowTokens"], 64000)

    def test_context_window_survives_container_rebuild(self) -> None:
        env_overrides = {"SKILL_MANAGER_SETTINGS_PATH": None}
        with AppTestHarness() as harness:
            harness.put_json("/api/settings/context-window", {"contextWindowTokens": 64000})
            settings_path = Path(harness.spec.xdg_config_home / "skill-manager" / "settings.json")
            self.assertEqual(settings_path.is_file(), True)
            saved = settings_path.read_text(encoding="utf-8")
            self.assertIn("64000", saved)

    def test_changing_context_window_updates_skills_usage(self) -> None:
        with AppTestHarness(mixed=True) as harness:
            first = harness.get_json("/api/skills")
            shared = next(row for row in first["rows"] if row["name"] == "Shared Audit")
            original_tokens = shared["contextUsage"]["estimatedTokens"]

            harness.put_json("/api/settings/context-window", {"contextWindowTokens": 64000})

            second = harness.get_json("/api/skills")
            updated = next(row for row in second["rows"] if row["name"] == "Shared Audit")
            detail = harness.get_json(f"/api/skills/{shared['skillRef']}")

        self.assertEqual(updated["contextUsage"]["estimatedTokens"], original_tokens)
        self.assertEqual(updated["contextUsage"]["contextWindowTokens"], 64000)
        self.assertEqual(detail["contextUsage"]["estimatedTokens"], original_tokens)
        self.assertEqual(detail["contextUsage"]["contextWindowTokens"], 64000)

    def test_changing_context_window_does_not_drop_disabled_harnesses(self) -> None:
        with AppTestHarness(mixed=True) as harness:
            harness.put_json("/api/settings/harnesses/codex/support", {"enabled": False})

            harness.put_json("/api/settings/context-window", {"contextWindowTokens": 64000})

            settings = harness.get_json("/api/settings")
            codex = next(item for item in settings["harnesses"] if item["harness"] == "codex")
            self.assertFalse(codex["supportEnabled"])
            self.assertEqual(settings["contextWindowTokens"], 64000)

    def test_toggle_harness_does_not_drop_context_window(self) -> None:
        with AppTestHarness() as harness:
            harness.put_json("/api/settings/context-window", {"contextWindowTokens": 64000})

            harness.put_json("/api/settings/harnesses/codex/support", {"enabled": False})

            settings = harness.get_json("/api/settings")
            self.assertEqual(settings["contextWindowTokens"], 64000)

    def test_put_context_window_rejects_non_positive_values(self) -> None:
        with AppTestHarness() as harness:
            for value in (0, -1):
                response = harness.put_json(
                    "/api/settings/context-window",
                    {"contextWindowTokens": value},
                    expected_status=422,
                )
                self.assertIn("contextWindowTokens", response["error"])

    def test_put_context_window_rejects_non_integer_values(self) -> None:
        with AppTestHarness() as harness:
            for body in (
                {"contextWindowTokens": True},
                {"contextWindowTokens": 1.5},
                {"contextWindowTokens": "64000"},
                {"contextWindowTokens": None},
                {},
            ):
                response = harness.put_json(
                    "/api/settings/context-window",
                    body,
                    expected_status=422,
                )
                self.assertIn("contextWindowTokens", response["error"])

    def test_skill_detail_returns_unavailable_when_skill_md_missing(self) -> None:
        from skill_manager.application.skills.context_estimator import SkillContextUsage
        from tests.support.fake_home import seed_skill_package

        def _seed(spec) -> None:
            seed_skill_package(spec.codex_legacy_root, "broken", "Broken Skill", body="hi")

        with AppTestHarness(fixture_factory=_seed) as harness:
            container = harness.container
            original_estimate = container.skills_queries.context_estimator.estimate

            def _patched(skill_root, context_window_tokens):
                if skill_root is not None and skill_root.name == "broken":
                    return SkillContextUsage(
                        estimated_tokens=None,
                        context_window_tokens=context_window_tokens,
                        usage_percent=None,
                        status="unavailable",
                        reason="skill_document_unreadable",
                    )
                return original_estimate(skill_root, context_window_tokens)

            container.skills_queries.context_estimator.estimate = _patched

            page = harness.get_json("/api/skills")
            broken_rows = [row for row in page["rows"] if row["name"] == "Broken Skill"]
            self.assertTrue(broken_rows, "fixture must surface at least one broken row")
            broken = broken_rows[0]
            self.assertEqual(broken["contextUsage"]["status"], "unavailable")
            self.assertEqual(broken["contextUsage"]["reason"], "skill_document_unreadable")
            detail = harness.get_json(f"/api/skills/{broken['skillRef']}")
            self.assertEqual(detail["contextUsage"]["status"], "unavailable")
            self.assertEqual(detail["contextUsage"]["reason"], "skill_document_unreadable")


if __name__ == "__main__":
    unittest.main()
