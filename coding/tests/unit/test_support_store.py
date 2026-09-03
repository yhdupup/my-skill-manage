from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from skill_manager.errors import MutationError
from skill_manager.harness.support_store import (
    CURRENT_SCHEMA_VERSION,
    DEFAULT_CONTEXT_WINDOW_TOKENS,
    HarnessSupportStore,
    SettingsDocument,
)


class HarnessSupportStoreTests(unittest.TestCase):
    def _store(self, directory: Path) -> HarnessSupportStore:
        return HarnessSupportStore(directory / "settings.json")

    def test_missing_file_returns_defaults_without_creating_one(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            store = self._store(root)
            document = store.load_document()
            preferences = store.load()
            self.assertEqual(document.schema_version, CURRENT_SCHEMA_VERSION)
            self.assertEqual(document.context_window_tokens, DEFAULT_CONTEXT_WINDOW_TOKENS)
            self.assertEqual(document.disabled_harnesses, ())
            self.assertEqual(preferences.disabled_harnesses, ())
            self.assertFalse((root / "settings.json").exists())

    def test_legacy_v0_file_with_disabled_harnesses_loads_with_default_window(self) -> None:
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "settings.json"
            path.write_text(json.dumps({"disabledHarnesses": ["codex", "claude"]}), encoding="utf-8")
            store = HarnessSupportStore(path)
            document = store.load_document()
            self.assertEqual(document.context_window_tokens, DEFAULT_CONTEXT_WINDOW_TOKENS)
            self.assertEqual(document.disabled_harnesses, ("claude", "codex"))
            self.assertEqual(document.schema_version, 0)

    def test_v1_settings_file_loads_both_known_fields(self) -> None:
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "settings.json"
            path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "contextWindowTokens": 64000,
                        "disabledHarnesses": ["codex"],
                    }
                ),
                encoding="utf-8",
            )
            store = HarnessSupportStore(path)
            document = store.load_document()
            self.assertEqual(document.context_window_tokens, 64000)
            self.assertEqual(document.disabled_harnesses, ("codex",))

    def test_set_context_window_preserves_disabled_harnesses(self) -> None:
        with TemporaryDirectory() as tempdir:
            store = self._store(Path(tempdir))
            store.set_enabled("codex", False)
            document = store.set_context_window_tokens(64000)
            self.assertEqual(document.context_window_tokens, 64000)
            self.assertEqual(document.disabled_harnesses, ("codex",))
            reloaded = HarnessSupportStore(store.path).load_document()
            self.assertEqual(reloaded.context_window_tokens, 64000)
            self.assertEqual(reloaded.disabled_harnesses, ("codex",))

    def test_set_enabled_preserves_context_window_and_unknown_fields(self) -> None:
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "settings.json"
            path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "contextWindowTokens": 32000,
                        "disabledHarnesses": [],
                        "experimental": {"flag": True},
                    }
                ),
                encoding="utf-8",
            )
            store = HarnessSupportStore(path)
            store.set_enabled("claude", False)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["contextWindowTokens"], 32000)
            self.assertEqual(payload["disabledHarnesses"], ["claude"])
            self.assertEqual(payload["experimental"], {"flag": True})

    def test_interleaved_mutations_do_not_revert_each_other(self) -> None:
        with TemporaryDirectory() as tempdir:
            store = self._store(Path(tempdir))
            store.set_enabled("codex", False)
            store.set_context_window_tokens(64000)
            store.set_enabled("claude", False)
            store.set_context_window_tokens(32000)
            document = store.load_document()
            self.assertEqual(document.context_window_tokens, 32000)
            self.assertEqual(document.disabled_harnesses, ("claude", "codex"))

    def test_written_document_includes_schema_version_one(self) -> None:
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "settings.json"
            store = HarnessSupportStore(path)
            store.set_enabled("codex", False)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schemaVersion"], 1)

    def test_invalid_window_value_falls_back_to_default(self) -> None:
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "settings.json"
            path.write_text(
                json.dumps({"schemaVersion": 1, "contextWindowTokens": -5}),
                encoding="utf-8",
            )
            store = HarnessSupportStore(path)
            document = store.load_document()
            self.assertEqual(document.context_window_tokens, DEFAULT_CONTEXT_WINDOW_TOKENS)

    def test_corrupt_json_mutation_raises_mutation_error_and_keeps_file(self) -> None:
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "settings.json"
            path.write_text("not json", encoding="utf-8")
            store = HarnessSupportStore(path)
            with self.assertRaises(MutationError):
                store.set_enabled("codex", False)
            self.assertEqual(path.read_text(encoding="utf-8"), "not json")

    def test_future_schema_mutation_refuses_to_overwrite(self) -> None:
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "settings.json"
            path.write_text(
                json.dumps(
                    {
                        "schemaVersion": CURRENT_SCHEMA_VERSION + 5,
                        "contextWindowTokens": 64000,
                    }
                ),
                encoding="utf-8",
            )
            store = HarnessSupportStore(path)
            with self.assertRaises(MutationError):
                store.set_context_window_tokens(128000)
            reloaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(reloaded["schemaVersion"], CURRENT_SCHEMA_VERSION + 5)
            self.assertEqual(reloaded["contextWindowTokens"], 64000)

    def test_write_failure_leaves_original_readable(self) -> None:
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "settings.json"
            original_payload = {
                "schemaVersion": 1,
                "contextWindowTokens": 128000,
                "disabledHarnesses": ["codex"],
            }
            path.write_text(json.dumps(original_payload), encoding="utf-8")
            original_text = path.read_text(encoding="utf-8")
            store = HarnessSupportStore(path)

            # Simulate atomic_write failure by patching the helper.
            from skill_manager.harness import support_store as support_store_module

            def _boom(*args, **kwargs):
                raise OSError("disk full")

            with unittest.mock.patch.object(support_store_module, "atomic_write_text", side_effect=_boom):
                with self.assertRaises(MutationError):
                    store.set_context_window_tokens(64000)

            # The file is still readable and holds the previous value.
            self.assertEqual(path.read_text(encoding="utf-8"), original_text)

    def test_default_document_is_pure(self) -> None:
        document = SettingsDocument(
            schema_version=1,
            context_window_tokens=128000,
            disabled_harnesses=(),
            extra={},
        )
        self.assertEqual(document.schema_version, 1)
        self.assertEqual(document.context_window_tokens, 128000)


if __name__ == "__main__":
    unittest.main()