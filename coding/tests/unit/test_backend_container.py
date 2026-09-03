from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from skill_manager.application import build_backend_container
from skill_manager.application.skills.manifest import SkillStoreEntry
from skill_manager.application.skills.package import fingerprint_package
from skill_manager.sources import ResolvedGitHubSkill

from tests.support.fake_home import (
    create_fake_home_spec,
    seed_divergent_source_fixture,
    seed_managed_linked_fixture,
    seed_mixed_fixture,
    seed_skill_package,
    seed_store_manifest,
)
from tests.support.marketplace_fixture import create_fixture_marketplace_service


class _StaticGitHubSource:
    def __init__(
        self,
        package_root: Path,
        *,
        repo: str = "example-org/skills",
        ref: str = "main",
        relative_path: str = ".",
    ) -> None:
        self.package_root = package_root
        self.repo = repo
        self.ref = ref
        self.relative_path = relative_path

    def fetch(self, locator: str, work_dir: Path) -> Path:
        return self.package_root

    def resolve(self, locator: str, work_dir: Path) -> ResolvedGitHubSkill:
        return ResolvedGitHubSkill(
            repo=self.repo,
            ref=self.ref,
            relative_path=self.relative_path,
            package_path=self.package_root,
            clone_dir=work_dir / self.repo.replace("/", "--"),
        )


class BackendContainerServiceTests(unittest.TestCase):
    def test_list_skills_groups_identical_local_copies_and_emits_two_public_statuses(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_mixed_fixture(spec)
            container = build_backend_container(spec.env())
            payload = container.skills_queries.list_skills()
            container.db.close()

            self.assertEqual(payload["summary"], {"managed": 1, "unmanaged": 2})

            shared_audit = next(row for row in payload["rows"] if row["name"] == "Shared Audit")
            trace_lens = next(row for row in payload["rows"] if row["name"] == "Trace Lens")
            policy_kit = next(row for row in payload["rows"] if row["name"] == "Policy Kit")

            self.assertEqual(shared_audit["displayStatus"], "Managed")
            self.assertEqual(
                shared_audit["actions"],
                {"canManage": False, "canStopManaging": False, "canDelete": True},
            )
            self.assertEqual(trace_lens["displayStatus"], "Unmanaged")
            self.assertEqual(
                trace_lens["actions"],
                {"canManage": True, "canStopManaging": False, "canDelete": False},
            )
            self.assertEqual(
                {cell["harness"] for cell in trace_lens["cells"] if cell["state"] == "found"},
                {"codex", "claude", "opencode"},
            )
            self.assertEqual(policy_kit["displayStatus"], "Unmanaged")

    def test_detail_and_source_status_are_split(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            package_root = seed_skill_package(
                spec.skills_store_root,
                "audit-skill",
                "Audit Skill",
                body="current managed version",
                source_kind="github",
                source_locator="github:example-org/audit-skill",
            )
            current_revision, _ = fingerprint_package(package_root)
            seed_store_manifest(
                spec,
                [
                    SkillStoreEntry(
                        package_dir="audit-skill",
                        declared_name="Audit Skill",
                        source_kind="github",
                        source_locator="github:example-org/audit-skill",
                        revision=f"{current_revision}-old",
                    )
                ],
            )

            container = build_backend_container(spec.env())
            payload = container.skills_queries.list_skills()
            audit = next(row for row in payload["rows"] if row["name"] == "Audit Skill")
            detail = container.skills_queries.get_skill_detail(audit["skillRef"])
            source_status = container.skills_queries.get_skill_source_status(audit["skillRef"])
            container.db.close()

            assert detail is not None
            assert source_status is not None

            self.assertEqual(detail["displayStatus"], "Managed")
            self.assertEqual(detail["attentionMessage"], "Local changes detected. Source updates are disabled.")
            self.assertNotIn("updateStatus", detail["actions"])
            self.assertEqual(source_status["updateStatus"], "local_changes_detected")
            self.assertEqual(detail["actions"]["stopManagingStatus"], "disabled_no_enabled")
            self.assertEqual(detail["actions"]["stopManagingHarnessLabels"], [])

    def test_divergent_source_backed_local_copies_become_separate_found_rows(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_divergent_source_fixture(spec)
            container = build_backend_container(spec.env())

            payload = container.skills_queries.list_skills()
            policy_rows = [row for row in payload["rows"] if row["name"] == "Policy Kit"]
            container.db.close()

            self.assertEqual(len(policy_rows), 2)
            self.assertTrue(all(row["displayStatus"] == "Unmanaged" for row in policy_rows))

    def test_settings_surface_store_issues(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_mixed_fixture(spec)
            container = build_backend_container(spec.env())

            settings = container.settings_queries.get_settings()
            container.db.close()

            self.assertEqual(settings["storage"]["skillsStorePath"], str(spec.skills_store_root))
            self.assertEqual(
                settings["storage"]["marketplaceCachePath"],
                str(spec.xdg_data_home / "skill-manager" / "marketplace"),
            )
            self.assertEqual(len(settings["harnesses"]), 7)
            codex = next(item for item in settings["harnesses"] if item["harness"] == "codex")
            self.assertIn("managedLocation", codex)
            self.assertIn("installed", codex)
            trae = next(item for item in settings["harnesses"] if item["harness"] == "trae")
            self.assertEqual(trae["harness"], "trae")
            self.assertEqual(trae["label"], "Trae CN")
            self.assertEqual(trae["managedLocation"], str(spec.home / ".trae-cn" / "skills"))
            self.assertTrue(trae["supportEnabled"])
            self.assertTrue(trae["installed"])
            self.assertNotIn("discoveryMode", codex)
            self.assertNotIn("centralStore", settings)
            self.assertNotIn("topology", settings)

    def test_skill_detail_exposes_document_markdown_for_shared_and_unmanaged_skills(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_mixed_fixture(spec)
            container = build_backend_container(spec.env())

            payload = container.skills_queries.list_skills()
            shared = next(row for row in payload["rows"] if row["name"] == "Shared Audit")
            found = next(row for row in payload["rows"] if row["name"] == "Trace Lens")

            shared_detail = container.skills_queries.get_skill_detail(shared["skillRef"])
            found_detail = container.skills_queries.get_skill_detail(found["skillRef"])
            container.db.close()

            assert shared_detail is not None
            assert found_detail is not None

            self.assertIn("Shared package fixture.", shared_detail["documentMarkdown"])
            self.assertIn("trace", found_detail["documentMarkdown"])
            self.assertNotIn("advanced", shared_detail)
            self.assertEqual(shared_detail["actions"]["stopManagingStatus"], "disabled_no_enabled")
            self.assertEqual(shared_detail["actions"]["stopManagingHarnessLabels"], [])
            self.assertIsNone(found_detail["actions"]["stopManagingStatus"])
            self.assertEqual(found_detail["actions"]["stopManagingHarnessLabels"], ["Claude"])
            self.assertEqual(found_detail["actions"]["deleteHarnessLabels"], ["Claude"])
            self.assertIsNone(found_detail["sourceLinks"])

    def test_skill_detail_orders_managed_locations_with_shared_store_first(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_managed_linked_fixture(spec)
            container = build_backend_container(spec.env())

            payload = container.skills_queries.list_skills()
            shared = next(row for row in payload["rows"] if row["name"] == "Shared Audit")
            detail = container.skills_queries.get_skill_detail(shared["skillRef"])
            container.db.close()

            assert detail is not None

            self.assertEqual([location["label"] for location in detail["locations"]], ["Shared Store", "Codex", "OpenClaw", "OpenCode"])
            self.assertEqual(detail["locations"][0]["path"], str(spec.skills_store_root / "shared-audit"))
            self.assertEqual(detail["locations"][1]["path"], str(spec.codex_root / "shared-audit"))
            self.assertEqual(detail["actions"]["stopManagingStatus"], "available")
            self.assertEqual(detail["actions"]["stopManagingHarnessLabels"], ["Codex"])

    def test_source_links_use_persisted_exact_folder_url(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            package_root = seed_skill_package(
                spec.skills_store_root,
                "shared-audit",
                "Shared Audit",
                body="Shared package fixture.",
                source_kind="github",
                source_locator="github:example-org/skills/shared-audit",
            )
            seed_store_manifest(
                spec,
                [
                    SkillStoreEntry(
                        package_dir="shared-audit",
                        declared_name="Shared Audit",
                        source_kind="github",
                        source_locator="github:example-org/skills/shared-audit",
                        revision=fingerprint_package(package_root)[0],
                        source_ref="main",
                        source_path="skills/shared-audit",
                    )
                ],
            )

            container = build_backend_container(spec.env())
            payload = container.skills_queries.list_skills()
            shared = next(row for row in payload["rows"] if row["name"] == "Shared Audit")
            detail = container.skills_queries.get_skill_detail(shared["skillRef"])
            source_status = container.skills_queries.get_skill_source_status(shared["skillRef"])
            container.db.close()

            assert detail is not None
            assert source_status is not None

            self.assertEqual(detail["sourceLinks"], {
                "repoLabel": "example-org/skills",
                "repoUrl": "https://github.com/example-org/skills",
                "folderUrl": "https://github.com/example-org/skills/tree/main/skills/shared-audit",
            })
            self.assertEqual(source_status["updateStatus"], "no_update_available")

    def test_source_links_fall_back_to_exact_github_resolution_for_legacy_entries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            package_root = seed_skill_package(
                spec.skills_store_root,
                "agent-browser",
                "agent-browser",
                body="Shared package fixture.",
                source_kind="github",
                source_locator="github:vercel-labs/agent-browser/agent-browser",
            )
            seed_store_manifest(
                spec,
                [
                    SkillStoreEntry(
                        package_dir="agent-browser",
                        declared_name="agent-browser",
                        source_kind="github",
                        source_locator="github:vercel-labs/agent-browser/agent-browser",
                        revision=fingerprint_package(package_root)[0],
                    )
                ],
            )

            container = build_backend_container(spec.env())
            container.skills_source_fetcher._github = _StaticGitHubSource(  # type: ignore[assignment]
                package_root,
                repo="vercel-labs/agent-browser",
                ref="main",
                relative_path="skills/agent-browser",
            )
            payload = container.skills_queries.list_skills()
            shared = next(row for row in payload["rows"] if row["name"] == "agent-browser")
            detail = container.skills_queries.get_skill_detail(shared["skillRef"])
            container.db.close()

            assert detail is not None

            self.assertEqual(detail["sourceLinks"], {
                "repoLabel": "vercel-labs/agent-browser",
                "repoUrl": "https://github.com/vercel-labs/agent-browser",
                "folderUrl": "https://github.com/vercel-labs/agent-browser/tree/main/skills/agent-browser",
            })

    def test_marketplace_queries_mark_matching_managed_source_as_installed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            package_root = seed_skill_package(
                spec.skills_store_root,
                "mode-switch",
                "Mode Switch",
                body="Managed package fixture.",
                source_kind="github",
                source_locator="github:example-org/skills/mode-switch",
            )
            seed_store_manifest(
                spec,
                [
                    SkillStoreEntry(
                        package_dir="mode-switch",
                        declared_name="Mode Switch",
                        source_kind="github",
                        source_locator="github:example-org/skills/mode-switch",
                        revision=fingerprint_package(package_root)[0],
                    )
                ],
            )

            container = build_backend_container(
                spec.env(),
                marketplace_catalog=create_fixture_marketplace_service(),
            )

            page = container.skills_marketplace_queries.popular_page()
            item = next(row for row in page["items"] if row["name"] == "Mode Switch")
            detail = container.skills_marketplace_queries.get_item_detail(item["id"])
            document = container.skills_marketplace_queries.get_item_document(item["id"])
            container.db.close()

            self.assertEqual(item["installation"], {
                "status": "installed",
                "installedSkillRef": "shared:mode-switch",
            })
            assert detail is not None
            assert document is not None
            self.assertEqual(detail["installation"], {
                "status": "installed",
                "installedSkillRef": "shared:mode-switch",
            })
            self.assertIn(document["status"], {"ready", "unavailable"})

    def test_list_skills_includes_context_usage_for_every_row(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_mixed_fixture(spec)
            container = build_backend_container(spec.env())

            payload = container.skills_queries.list_skills()
            container.db.close()

            self.assertTrue(payload["rows"], "fixture should produce rows")
            for row in payload["rows"]:
                self.assertIn("contextUsage", row)
                usage = row["contextUsage"]
                self.assertIn("estimatedTokens", usage)
                self.assertIn("contextWindowTokens", usage)
                self.assertIn("usagePercent", usage)
                self.assertIn("status", usage)
                self.assertEqual(usage["contextWindowTokens"], 128000)

    def test_skill_detail_includes_matching_context_usage(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_mixed_fixture(spec)
            container = build_backend_container(spec.env())

            page = container.skills_queries.list_skills()
            shared_audit = next(row for row in page["rows"] if row["name"] == "Shared Audit")
            detail = container.skills_queries.get_skill_detail(shared_audit["skillRef"])
            container.db.close()

            assert detail is not None
            self.assertIn("contextUsage", detail)
            self.assertEqual(
                detail["contextUsage"]["status"],
                shared_audit["contextUsage"]["status"],
            )
            self.assertEqual(
                detail["contextUsage"]["estimatedTokens"],
                shared_audit["contextUsage"]["estimatedTokens"],
            )
            self.assertEqual(detail["contextUsage"]["contextWindowTokens"], 128000)

    def test_changing_context_window_updates_percentage_and_keeps_tokens(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_mixed_fixture(spec)
            container = build_backend_container(spec.env())

            first = container.skills_queries.list_skills()
            shared_audit = next(row for row in first["rows"] if row["name"] == "Shared Audit")
            original_tokens = shared_audit["contextUsage"]["estimatedTokens"]

            container.settings_mutations.set_context_window_tokens(64000)
            updated = container.skills_queries.list_skills()
            updated_row = next(row for row in updated["rows"] if row["name"] == "Shared Audit")
            updated_detail = container.skills_queries.get_skill_detail(shared_audit["skillRef"])
            container.db.close()

            self.assertEqual(updated_row["contextUsage"]["estimatedTokens"], original_tokens)
            self.assertEqual(updated_row["contextUsage"]["contextWindowTokens"], 64000)
            assert updated_detail is not None
            self.assertEqual(updated_detail["contextUsage"]["estimatedTokens"], original_tokens)
            self.assertEqual(updated_detail["contextUsage"]["contextWindowTokens"], 64000)
            # The percentage must use the new denominator.
            if original_tokens:
                expected = round(original_tokens / 64000 * 100, 2)
                self.assertEqual(updated_row["contextUsage"]["usagePercent"], expected)

    def test_unreadable_skill_md_returns_unavailable_without_breaking_other_rows(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_skill_package(
                spec.codex_legacy_root,
                "good-skill",
                "Good Skill",
                body="a" * 200,
            )
            seed_skill_package(
                spec.codex_legacy_root,
                "broken-skill",
                "Broken Skill",
                body="b" * 200,
            )

            container = build_backend_container(spec.env())

            # Replace the SKILL.md of one Skill with a symlink pointing to a
            # deleted file so the inventory scan still picks it up but the
            # estimator fails when reading it back.  Use the actual SKILL.md
            # path resolution that the query service uses.
            from skill_manager.application.skills.queries import SkillsQueryService
            from skill_manager.application.skills.context_estimator import SkillContextEstimator
            from skill_manager.harness.support_store import HarnessSupportStore

            # Replace the estimator's read with one that returns unreadable
            # for the broken skill while leaving the rest untouched.
            original_estimate = container.skills_queries.context_estimator.estimate

            def _patched_estimate(skill_root, context_window_tokens):
                if skill_root is not None and skill_root.name == "broken-skill":
                    from skill_manager.application.skills.context_estimator import SkillContextUsage

                    return SkillContextUsage(
                        estimated_tokens=None,
                        context_window_tokens=context_window_tokens,
                        usage_percent=None,
                        status="unavailable",
                        reason="skill_document_unreadable",
                    )
                return original_estimate(skill_root, context_window_tokens)

            container.skills_queries.context_estimator.estimate = _patched_estimate
            payload = container.skills_queries.list_skills()
            container.db.close()

            by_name = {row["name"]: row for row in payload["rows"]}
            self.assertIn("Good Skill", by_name)
            self.assertIn("Broken Skill", by_name)
            self.assertEqual(by_name["Good Skill"]["contextUsage"]["status"], "normal")
            self.assertEqual(by_name["Broken Skill"]["contextUsage"]["status"], "unavailable")
            self.assertEqual(
                by_name["Broken Skill"]["contextUsage"]["reason"],
                "skill_document_unreadable",
            )

    def test_settings_query_returns_default_context_window(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            container = build_backend_container(spec.env())
            settings = container.settings_queries.get_settings()
            container.db.close()

            self.assertEqual(settings["contextWindowTokens"], 128000)

    def test_settings_mutation_returns_saved_window(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            container = build_backend_container(spec.env())
            result = container.settings_mutations.set_context_window_tokens(64000)
            container.db.close()

            self.assertTrue(result["ok"])
            self.assertEqual(result["contextWindowTokens"], 64000)

    def test_managed_skill_context_usage_prefers_shared_package(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            shared = seed_skill_package(
                spec.skills_store_root,
                "shared-skill",
                "Shared Skill",
                body="a" * 80,
            )
            shared_tokens = fingerprint_package(shared)
            seed_store_manifest(
                spec,
                [
                    SkillStoreEntry(
                        package_dir="shared-skill",
                        declared_name="Shared Skill",
                        source_kind="github",
                        source_locator="github:example-org/shared-skill",
                        revision=shared_tokens[0],
                    )
                ],
            )
            # Create a divergent copy on the harness side. The estimator
            # should still use the shared package content.
            seed_skill_package(
                spec.codex_root,
                "shared-skill",
                "Shared Skill",
                body="z" * 800,
            )

            container = build_backend_container(spec.env())
            page = container.skills_queries.list_skills()
            container.db.close()

            shared_row = next(row for row in page["rows"] if row["name"] == "Shared Skill")
            # 80 ascii chars + ~35 chars of frontmatter/heading = 115 ascii,
            # which rounds up to 29 tokens — not 200 from the harness copy.
            self.assertEqual(shared_row["contextUsage"]["estimatedTokens"], 29)


if __name__ == "__main__":
    unittest.main()
