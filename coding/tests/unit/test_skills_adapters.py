from __future__ import annotations

from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from skill_manager.application.skills.adapters import build_skills_adapters
from skill_manager.directory_links import create_directory_link, is_directory_link
from skill_manager.errors import MutationError
from skill_manager.harness import HarnessKernelService, HarnessSupportStore

from tests.support.fake_home import (
    create_fake_home_spec,
    seed_macos_app,
    seed_skill_package,
    write_cli_stub,
)


def _adapter(harness: str, spec) :
    kernel = HarnessKernelService.from_environment(
        spec.env(),
        support_store=HarnessSupportStore(spec.root / "settings.json"),
    )
    return next(adapter for adapter in build_skills_adapters(kernel) if adapter.harness == harness)


class SkillsAdapterTests(unittest.TestCase):
    def test_adapter_scans_discovery_roots_and_reports_installation(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_skill_package(spec.codex_legacy_root, "trace-lens", "Trace Lens")
            seed_skill_package(spec.openclaw_managed_root, "watch", "Workspace Watch")
            seed_skill_package(spec.hermes_skills_root / "debugging", "trace", "Hermes Trace")
            hub_lock = spec.hermes_skills_root / ".hub" / "lock.json"
            hub_lock.parent.mkdir(parents=True, exist_ok=True)
            hub_lock.write_text(
                """{
  \"version\": 1,
  \"installed\": {
    \"trace\": {
      \"source\": \"github\",
      \"identifier\": \"github/example/hermes-trace\",
      \"trust_level\": \"community\",
      \"install_path\": \"debugging/trace\"
    }
  }
}
""",
                encoding="utf-8",
            )

            codex = _adapter("codex", spec)
            claude = _adapter("claude", spec)
            openclaw = _adapter("openclaw", spec)
            hermes = _adapter("hermes", spec)

            codex_scan = codex.scan()
            claude_scan = claude.scan()
            openclaw_scan = openclaw.scan()
            hermes_scan = hermes.scan()

            self.assertTrue(codex_scan.installed)
            self.assertEqual(codex_scan.skills[0].package.declared_name, "Trace Lens")
            self.assertTrue(claude_scan.installed)
            self.assertEqual(claude_scan.skills, ())
            self.assertTrue(openclaw_scan.installed)
            self.assertEqual(
                [skill.package.declared_name for skill in openclaw_scan.skills],
                ["Workspace Watch"],
            )
            self.assertTrue(hermes_scan.installed)
            self.assertEqual(
                [skill.package.declared_name for skill in hermes_scan.skills],
                ["Hermes Trace"],
            )
            self.assertEqual(hermes_scan.skills[0].package.source.kind, "github")
            self.assertEqual(
                hermes_scan.skills[0].package.source.locator,
                "github/example/hermes-trace",
            )

    def test_hermes_scan_only_includes_external_hub_skills_without_touching_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            bundled = seed_skill_package(
                spec.hermes_skills_root / "builtin",
                "bundled-core",
                "Bundled Core",
            )
            official = seed_skill_package(
                spec.hermes_skills_root / "optional",
                "official-helper",
                "Official Helper",
            )
            local = seed_skill_package(
                spec.hermes_skills_root / "local",
                "user-helper",
                "User Helper",
            )
            community_hub = seed_skill_package(
                spec.hermes_skills_root / "hub",
                "community-helper",
                "Community Helper",
            )
            (bundled / "SKILL.md").write_bytes(b"\xff")
            (official / "SKILL.md").write_bytes(b"\xff")
            (local / "SKILL.md").write_bytes(b"\xff")
            (spec.hermes_skills_root / ".bundled_manifest").write_text(
                "Bundled Core:0123456789abcdef\n",
                encoding="utf-8",
            )
            hub_lock = spec.hermes_skills_root / ".hub" / "lock.json"
            hub_lock.parent.mkdir(parents=True, exist_ok=True)
            hub_lock.write_text(
                """{
  "version": 1,
  "installed": {
    "official-helper": {
      "source": "official",
      "identifier": "official/optional/official-helper",
      "trust_level": "builtin",
      "install_path": "optional/official-helper",
      "metadata": {"backfilled_from": "optional-skills"}
    },
    "community-helper": {
      "source": "github",
      "identifier": "github/example/community-helper",
      "trust_level": "community",
      "install_path": "hub/community-helper"
    }
  }
}
""",
                encoding="utf-8",
            )
            hermes = _adapter("hermes", spec)

            scan = hermes.scan()

            self.assertEqual(
                [skill.package.declared_name for skill in scan.skills],
                ["Community Helper"],
            )
            self.assertEqual(scan.skills[0].package.source.kind, "github")
            self.assertEqual(scan.skills[0].package.source.locator, "github/example/community-helper")
            self.assertIn("Bundled Core", scan.excluded_skill_names)
            self.assertIn("official-helper", scan.excluded_skill_names)
            self.assertIn("user-helper", scan.excluded_skill_names)
            self.assertTrue((bundled / "SKILL.md").is_file())
            self.assertTrue((official / "SKILL.md").is_file())
            self.assertFalse(is_directory_link(bundled))
            self.assertFalse(is_directory_link(official))
            self.assertTrue((local / "SKILL.md").is_file())
            self.assertTrue((community_hub / "SKILL.md").is_file())

    def test_adapter_reports_missing_cli_as_not_installed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir), seed_openclaw_state=False)

            openclaw = _adapter("openclaw", spec)

            self.assertFalse(openclaw.status().installed)
            self.assertEqual(openclaw.scan().skills, ())

    def test_cursor_skills_use_skills_root_and_ignore_skills_cursor(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_skill_package(spec.cursor_root, "managed-cursor", "Managed Cursor")
            seed_skill_package(spec.cursor_owned_root, "cursor-built", "Cursor Built")

            cursor = _adapter("cursor", spec)
            scan = cursor.scan()

            self.assertEqual(cursor.managed_root, spec.cursor_root)
            self.assertEqual(
                [skill.package.declared_name for skill in scan.skills],
                ["Managed Cursor"],
            )

    def test_codex_app_probe_keeps_skills_adapter_installed_without_cli(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            spec.cli_path("codex").unlink()
            seed_macos_app(
                spec.home / "Applications" / "Codex.app",
                bundle_identifier="com.openai.codex",
                executable="Codex",
            )

            codex = _adapter("codex", spec)
            kernel = HarnessKernelService.from_environment(
                spec.env(),
                support_store=HarnessSupportStore(spec.root / "settings.json"),
            )
            codex_status = next(
                status for status in kernel.harness_statuses() if status.harness == "codex"
            )

            self.assertTrue(codex.status().installed)
            self.assertTrue(codex_status.installed)

    def test_cursor_app_probe_keeps_skills_adapter_installed_without_cli(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            spec.cli_path("cursor-agent").unlink()
            seed_macos_app(
                spec.home / "Applications" / "Cursor.app",
                bundle_identifier="com.todesktop.cursor",
                executable="Cursor",
            )

            cursor = _adapter("cursor", spec)
            kernel = HarnessKernelService.from_environment(
                spec.env(),
                support_store=HarnessSupportStore(spec.root / "settings.json"),
            )
            cursor_status = next(
                status for status in kernel.harness_statuses() if status.harness == "cursor"
            )

            self.assertTrue(cursor.status().installed)
            self.assertTrue(cursor_status.installed)
            self.assertEqual(cursor_status.managed_location, spec.cursor_root)

    def test_codex_vscode_extension_probe_detects_codex_without_path_entry(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            spec.cli_path("codex").unlink()
            extension_binary = (
                spec.home
                / ".vscode"
                / "extensions"
                / "openai.chatgpt-1.2.3-darwin-arm64"
                / "bin"
                / "macos-aarch64"
                / "codex"
            )
            extension_binary.parent.mkdir(parents=True)
            write_cli_stub(extension_binary, "codex")
            (extension_binary.parents[2] / "package.json").write_text(
                '{"name":"chatgpt","publisher":"openai","version":"1.2.3"}',
                encoding="utf-8",
            )

            codex = _adapter("codex", spec)
            kernel = HarnessKernelService.from_environment(
                spec.env(),
                support_store=HarnessSupportStore(spec.root / "settings.json"),
            )
            codex_status = next(
                status for status in kernel.harness_statuses() if status.harness == "codex"
            )

            self.assertTrue(codex.status().installed)
            self.assertTrue(codex_status.installed)

    def test_trae_scan_only_includes_skill_root_entries_and_ignores_builtins(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            seed_skill_package(spec.trae_root, "managed-trace", "Managed Trace")
            seed_skill_package(spec.trae_root, "builtin", "Builtin Core")
            seed_skill_package(spec.trae_root, "builtin_skills", "Built-in Skills Core")
            seed_skill_package(spec.trae_root, "plugins", "Plugin Core")
            (spec.home / ".trae" / "skills").mkdir(parents=True, exist_ok=True)
            (spec.home / ".trae" / "skills" / "project-trace").mkdir(parents=True, exist_ok=True)
            (spec.home / ".trae" / "skills" / "project-trace" / "SKILL.md").write_text(
                "# Project Trace\n",
                encoding="utf-8",
            )

            trae = _adapter("trae", spec)
            scan = trae.scan()

            self.assertEqual([skill.package.declared_name for skill in scan.skills], ["Managed Trace"])
            self.assertIn("builtin", scan.excluded_skill_names)
            self.assertIn("builtin_skills", scan.excluded_skill_names)
            self.assertIn("plugins", scan.excluded_skill_names)
            self.assertNotIn("Project Trace", scan.excluded_skill_names)
            self.assertTrue(
                (spec.home / ".trae" / "skills" / "project-trace" / "SKILL.md").is_file()
            )

    def test_trae_app_probe_keeps_skills_adapter_installed_without_cli(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            spec.cli_path("trae").unlink()
            seed_macos_app(
                spec.home / "Applications" / "Trae CN.app",
                bundle_identifier="cn.trae.app",
                executable="Electron",
            )

            trae = _adapter("trae", spec)
            kernel = HarnessKernelService.from_environment(
                spec.env(),
                support_store=HarnessSupportStore(spec.root / "settings.json"),
            )
            trae_status = next(
                status for status in kernel.harness_statuses() if status.harness == "trae"
            )

            self.assertTrue(trae.status().installed)
            self.assertTrue(trae_status.installed)
            self.assertEqual(trae_status.managed_location, spec.trae_root)

    def test_enable_creates_symlink(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            package = seed_skill_package(spec.skills_store_root, "audit", "Audit")
            codex = _adapter("codex", spec)

            codex.enable_shared_package(package)

            link = spec.codex_root / "audit"
            self.assertTrue(is_directory_link(link))
            self.assertEqual(link.resolve(), package.resolve())

    def test_enable_refuses_real_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            package = seed_skill_package(spec.skills_store_root, "audit", "Audit")
            seed_skill_package(spec.codex_root, "audit", "Local Audit")
            codex = _adapter("codex", spec)

            with self.assertRaises(MutationError) as ctx:
                codex.enable_shared_package(package)

            self.assertIn("real directory", str(ctx.exception))

    def test_adopt_local_copy_replaces_dir_with_symlink(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            store_pkg = seed_skill_package(spec.skills_store_root, "audit", "Audit")
            harness_pkg = seed_skill_package(spec.codex_root, "audit", "Audit")
            codex = _adapter("codex", spec)

            codex.adopt_local_copy(harness_pkg, store_pkg)

            self.assertTrue(is_directory_link(harness_pkg))
            self.assertEqual(harness_pkg.resolve(), store_pkg.resolve())

    def test_materialize_binding_restores_real_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            store_pkg = seed_skill_package(
                spec.skills_store_root,
                "audit",
                "Audit",
                body="shared version",
            )
            link = spec.codex_root / "audit"
            create_directory_link(link, store_pkg)
            codex = _adapter("codex", spec)

            codex.materialize_binding("audit", store_pkg)

            self.assertTrue(link.is_dir())
            self.assertFalse(is_directory_link(link))
            self.assertIn("shared version", (link / "SKILL.md").read_text(encoding="utf-8"))

    def test_has_binding_recognizes_directory_link_with_missing_target(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            package = seed_skill_package(spec.skills_store_root, "audit", "Audit")
            link = spec.codex_root / "audit"
            create_directory_link(link, package)
            codex = _adapter("codex", spec)

            shutil.rmtree(package)

            self.assertTrue(is_directory_link(link))
            self.assertTrue(codex.has_binding("audit"))

    def test_hermes_enable_creates_symlink_under_default_category(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            package = seed_skill_package(spec.skills_store_root, "audit", "Audit")
            hermes = _adapter("hermes", spec)

            hermes.enable_shared_package(package)

            link = spec.hermes_skills_root / "skill-manager" / "audit"
            self.assertTrue(is_directory_link(link))
            self.assertEqual(link.resolve(), package.resolve())
            self.assertTrue(hermes.has_binding("audit"))

    def test_hermes_enable_ignores_real_directory_in_existing_category(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            package = seed_skill_package(spec.skills_store_root, "audit", "Audit")
            hermes_owned = seed_skill_package(
                spec.hermes_skills_root / "local",
                "audit",
                "Hermes Audit",
            )
            hermes = _adapter("hermes", spec)

            self.assertFalse(hermes.has_binding("audit"))

            hermes.enable_shared_package(package)

            link = spec.hermes_skills_root / "skill-manager" / "audit"
            self.assertTrue(is_directory_link(link))
            self.assertEqual(link.resolve(), package.resolve())
            self.assertTrue((hermes_owned / "SKILL.md").is_file())
            self.assertFalse(is_directory_link(hermes_owned))

    def test_hermes_disable_finds_symlink_in_existing_category(self) -> None:
        with TemporaryDirectory() as temp_dir:
            spec = create_fake_home_spec(Path(temp_dir))
            package = seed_skill_package(spec.skills_store_root, "audit", "Audit")
            link = spec.hermes_skills_root / "custom" / "audit"
            link.parent.mkdir(parents=True, exist_ok=True)
            create_directory_link(link, package)
            hermes = _adapter("hermes", spec)

            hermes.disable_shared_package("audit")

            self.assertFalse(link.exists())
            self.assertFalse(is_directory_link(link))


if __name__ == "__main__":
    unittest.main()
