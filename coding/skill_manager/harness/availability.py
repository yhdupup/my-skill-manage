from __future__ import annotations

from collections.abc import Sequence
import os
from pathlib import Path
import plistlib
import subprocess
import shutil

from skill_manager.platform_context import PlatformName


VERSION_PROBE_TIMEOUT_SECONDS = 3.0


def probe_command_succeeds(argv: Sequence[str], *, timeout_seconds: float) -> bool:
    """Run a short health probe against an already-resolved executable.

    A timeout counts as success. Reaching it means the OS launched the
    executable and it was merely slow, which is what the probe asks about:
    some CLIs run update or environment checks on a cold start, and a slow
    one must not disappear from the UI.
    """
    try:
        result = subprocess.run(
            list(argv),
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return True
    except OSError:
        return False
    return result.returncode == 0


def command_is_available(
    command: str,
    *,
    path_env: str | None,
    platform: PlatformName,
) -> bool:
    executable = shutil.which(command, path=path_env)
    if executable is None:
        return False
    # A resolved executable can still be a stale shim or a same-named broken
    # command. Launching a side-effect-free version probe verifies that the
    # current user can actually run it on every supported platform.
    return probe_command_succeeds(
        [executable, "--version"],
        timeout_seconds=VERSION_PROBE_TIMEOUT_SECONDS,
    )


def any_command_is_available(
    commands: tuple[str, ...],
    *,
    path_env: str | None,
    platform: PlatformName,
) -> bool:
    return any(
        command_is_available(
            command,
            path_env=path_env,
            platform=platform,
        )
        for command in commands
    )


def harness_installation_is_available(
    commands: tuple[str, ...],
    *,
    path_env: str | None,
    platform: PlatformName,
    allow_app_probe: bool = False,
    app_probe_paths: tuple[Path, ...] = (),
) -> bool:
    """Return whether a supported harness is actually installed.

    CLI availability is authoritative for every harness. Desktop application
    paths are accepted only for profiles whose Skill integration is known to
    work through the app, preventing leftover config folders from producing
    false positives.
    """
    if any_command_is_available(commands, path_env=path_env, platform=platform):
        return True
    if not allow_app_probe:
        return False
    return any(_installation_path_is_valid(path) for path in app_probe_paths)


def _installation_path_is_valid(path: Path) -> bool:
    if path.suffix.casefold() == ".app":
        return _valid_macos_app_bundle(path)
    return path.is_file() and os.access(path, os.X_OK)


def _valid_macos_app_bundle(path: Path) -> bool:
    info_path = path / "Contents" / "Info.plist"
    if not path.is_dir() or not info_path.is_file():
        return False
    try:
        with info_path.open("rb") as handle:
            info = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException):
        return False
    executable = info.get("CFBundleExecutable")
    bundle_identifier = info.get("CFBundleIdentifier")
    if not isinstance(executable, str) or not executable.strip():
        return False
    if not isinstance(bundle_identifier, str) or not bundle_identifier.strip():
        return False
    executable_path = path / "Contents" / "MacOS" / executable
    return executable_path.is_file() and os.access(executable_path, os.X_OK)


__all__ = [
    "any_command_is_available",
    "command_is_available",
    "harness_installation_is_available",
    "probe_command_succeeds",
]
