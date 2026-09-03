from __future__ import annotations

import plistlib
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from skill_manager.harness.availability import (
    any_command_is_available,
    command_is_available,
    harness_installation_is_available,
)


class HarnessAvailabilityTests(unittest.TestCase):
    def test_multiple_probes_accept_first_working_windows_command(self) -> None:
        with mock.patch(
            "skill_manager.harness.availability.command_is_available",
            side_effect=lambda command, **_kwargs: command == "cursor",
        ) as probe_mock:
            available = any_command_is_available(
                ("cursor-agent", "cursor"),
                path_env="C:/bin",
                platform="windows",
            )

        self.assertTrue(available)
        self.assertEqual(
            [call.args[0] for call in probe_mock.call_args_list],
            ["cursor-agent", "cursor"],
        )

    def test_unix_discovery_requires_an_invokable_version_probe(self) -> None:
        completed = subprocess.CompletedProcess(["codex", "--version"], 0)
        with (
            mock.patch("skill_manager.harness.availability.shutil.which", return_value="/bin/codex"),
            mock.patch(
                "skill_manager.harness.availability.subprocess.run",
                return_value=completed,
            ) as run_mock,
        ):
            available = command_is_available("codex", path_env="/bin", platform="linux")

        self.assertTrue(available)
        run_mock.assert_called_once()

    def test_windows_discovery_requires_invokable_command(self) -> None:
        with (
            mock.patch(
                "skill_manager.harness.availability.shutil.which",
                return_value="C:/restricted/codex.exe",
            ),
            mock.patch(
                "skill_manager.harness.availability.subprocess.run",
                side_effect=PermissionError("access denied"),
            ),
        ):
            available = command_is_available("codex", path_env="C:/restricted", platform="windows")

        self.assertFalse(available)

    def test_windows_discovery_accepts_successful_version_probe(self) -> None:
        completed = subprocess.CompletedProcess(["codex", "--version"], 0)
        with (
            mock.patch(
                "skill_manager.harness.availability.shutil.which",
                return_value="C:/bin/codex.cmd",
            ),
            mock.patch(
                "skill_manager.harness.availability.subprocess.run",
                return_value=completed,
            ),
        ):
            available = command_is_available("codex", path_env="C:/bin", platform="windows")

        self.assertTrue(available)

    def test_windows_discovery_accepts_slow_but_invokable_command(self) -> None:
        with (
            mock.patch(
                "skill_manager.harness.availability.shutil.which",
                return_value="C:/bin/hermes.exe",
            ),
            mock.patch(
                "skill_manager.harness.availability.subprocess.run",
                side_effect=subprocess.TimeoutExpired(["hermes", "--version"], timeout=3),
            ),
        ):
            available = command_is_available("hermes", path_env="C:/bin", platform="windows")

        self.assertTrue(available)

    def test_installation_probe_accepts_verified_desktop_app_for_app_capable_harness(self) -> None:
        with TemporaryDirectory() as temp_dir:
            app_path = Path(temp_dir) / "Cursor.app"
            executable = app_path / "Contents" / "MacOS" / "Cursor"
            executable.parent.mkdir(parents=True)
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            with (app_path / "Contents" / "Info.plist").open("wb") as handle:
                plistlib.dump(
                    {"CFBundleIdentifier": "com.todesktop.cursor", "CFBundleExecutable": "Cursor"},
                    handle,
                )
            with mock.patch(
                "skill_manager.harness.availability.any_command_is_available",
                return_value=False,
            ):
                available = harness_installation_is_available(
                    ("cursor-agent", "cursor"),
                    path_env="/empty",
                    platform="macos",
                    allow_app_probe=True,
                    app_probe_paths=(app_path,),
                )

        self.assertTrue(available)

    def test_installation_probe_rejects_empty_app_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            app_path = Path(temp_dir) / "Cursor.app"
            app_path.mkdir()
            with mock.patch(
                "skill_manager.harness.availability.any_command_is_available",
                return_value=False,
            ):
                available = harness_installation_is_available(
                    ("cursor",),
                    path_env="/empty",
                    platform="macos",
                    allow_app_probe=True,
                    app_probe_paths=(app_path,),
                )

        self.assertFalse(available)

    def test_installation_probe_ignores_leftover_app_path_for_cli_only_harness(self) -> None:
        with TemporaryDirectory() as temp_dir:
            stale_path = Path(temp_dir) / "Claude.app"
            stale_path.mkdir()
            with mock.patch(
                "skill_manager.harness.availability.any_command_is_available",
                return_value=False,
            ):
                available = harness_installation_is_available(
                    ("claude",),
                    path_env="/empty",
                    platform="macos",
                    allow_app_probe=False,
                    app_probe_paths=(stale_path,),
                )

        self.assertFalse(available)


if __name__ == "__main__":
    unittest.main()
