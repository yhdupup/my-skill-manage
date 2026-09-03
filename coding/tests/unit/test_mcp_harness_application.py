from __future__ import annotations

import unittest
from pathlib import Path

from skill_manager.application.mcp.harness_application import McpHarnessApplication
from skill_manager.application.mcp.store import McpServerSpec, McpSource


def _spec() -> McpServerSpec:
    return McpServerSpec(
        name="exa",
        display_name="Exa",
        source=McpSource.marketplace("exa"),
        transport="http",
        url="https://mcp.exa.ai",
    )


class _Adapter:
    label = "Harness"
    logo_key = None
    config_path = Path("/tmp/config.json")

    def __init__(self, harness: str, *, fail_enable: bool = False) -> None:
        self.harness = harness
        self.fail_enable = fail_enable
        self.enabled: list[str] = []

    def enable_server(self, spec: McpServerSpec) -> None:
        if self.fail_enable:
            raise RuntimeError(f"{self.harness} write failed")
        self.enabled.append(spec.name)

    def disable_server(self, _name: str) -> None:
        return None


class _ReadModels:
    def __init__(self, adapters: tuple[_Adapter, ...]) -> None:
        self.adapters = adapters
        self.invalidated = 0

    def enabled_adapters(self) -> tuple[_Adapter, ...]:
        return self.adapters

    def enabled_writable_adapters(self) -> tuple[_Adapter, ...]:
        return self.adapters

    def enabled_addressable_adapters(self) -> tuple[_Adapter, ...]:
        return self.adapters

    def invalidate(self) -> None:
        self.invalidated += 1


class HarnessApplicationTests(unittest.TestCase):
    def test_enable_many_commits_once_after_partial_success(self) -> None:
        read_models = _ReadModels(
            (
                _Adapter("cursor", fail_enable=True),
                _Adapter("claude"),
            )
        )
        app = McpHarnessApplication(read_models)  # type: ignore[arg-type]
        commits = 0

        def commit() -> None:
            nonlocal commits
            commits += 1

        result = app.enable_many(_spec(), {"cursor", "claude"}, commit=commit)

        self.assertFalse(result.ok)
        self.assertEqual(result.succeeded, ["claude"])
        self.assertEqual(result.failed[0]["harness"], "cursor")
        self.assertEqual(commits, 1)
        self.assertEqual(read_models.invalidated, 1)

    def test_enable_many_skips_commit_when_all_writes_fail(self) -> None:
        read_models = _ReadModels(
            (
                _Adapter("cursor", fail_enable=True),
                _Adapter("claude", fail_enable=True),
            )
        )
        app = McpHarnessApplication(read_models)  # type: ignore[arg-type]
        commits = 0

        def commit() -> None:
            nonlocal commits
            commits += 1

        result = app.enable_many(_spec(), {"cursor", "claude"}, commit=commit)

        self.assertFalse(result.ok)
        self.assertEqual(result.succeeded, [])
        self.assertEqual(commits, 0)
        self.assertEqual(read_models.invalidated, 0)


if __name__ == "__main__":
    unittest.main()
