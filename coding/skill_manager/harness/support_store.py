from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping

from skill_manager.atomic_files import atomic_write_text, file_lock
from skill_manager.errors import MutationError


CURRENT_SCHEMA_VERSION = 1
LEGACY_SCHEMA_VERSION = 0
DEFAULT_CONTEXT_WINDOW_TOKENS = 128000


@dataclass(frozen=True)
class HarnessSupportPreferences:
    disabled_harnesses: tuple[str, ...] = ()

    def is_enabled(self, harness: str) -> bool:
        return harness not in self.disabled_harnesses


@dataclass(frozen=True)
class SettingsDocument:
    """In-memory representation of the persisted settings file.

    The on-disk document is treated as a small key/value map that can grow
    over time. Each known field is parsed defensively; unknown top-level
    keys are preserved through mutations so future settings do not get
    dropped by accident.
    """

    schema_version: int
    context_window_tokens: int
    disabled_harnesses: tuple[str, ...]
    extra: Mapping[str, Any] = field(default_factory=dict)


class HarnessSupportStore:
    """Persist and load application settings.

    The store evolved from a single ``disabledHarnesses`` key into a
    versioned settings document that can safely coexist with future
    additions. Every mutation re-reads the file inside the same lock and
    writes back the merged document atomically so unrelated settings are
    never lost.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    # ------------------------------------------------------------------
    # Backwards-compatible public API
    # ------------------------------------------------------------------
    def load(self) -> HarnessSupportPreferences:
        document = self._read_document()
        return HarnessSupportPreferences(disabled_harnesses=document.disabled_harnesses)

    def set_enabled(self, harness: str, enabled: bool) -> HarnessSupportPreferences:
        preferences = self.update(lambda document: _toggle_harness(document, harness, enabled))
        return preferences

    def enabled_harnesses(self, supported_harnesses: tuple[str, ...]) -> tuple[str, ...]:
        preferences = self.load()
        return tuple(harness for harness in supported_harnesses if preferences.is_enabled(harness))

    # ------------------------------------------------------------------
    # New settings API (introduced in the context estimator stage)
    # ------------------------------------------------------------------
    def load_document(self) -> SettingsDocument:
        return self._read_document()

    def context_window_tokens(self) -> int:
        return self._read_document().context_window_tokens

    def update(self, mutator) -> SettingsDocument:
        """Apply ``mutator`` to the current document and persist the result.

        ``mutator`` receives the freshly parsed :class:`SettingsDocument` and
        must return a new :class:`SettingsDocument` instance (or a value that
        can be coerced to it via :func:`_coerce_document`).
        """

        with file_lock(self.path.with_suffix(".lock")):
            try:
                current = self._read_document_unlocked()
                candidate = mutator(current)
            except _MutationAbort as abort:
                raise abort.error from None
            next_document = _coerce_document(candidate, current)
            _validate_document(next_document)
            try:
                self._write_document_unlocked(next_document)
            except MutationError:
                raise
            except Exception as exc:  # pragma: no cover - safety net
                raise MutationError(f"failed to persist settings: {exc}", status=503) from exc
            return next_document

    def set_context_window_tokens(self, value: int) -> SettingsDocument:
        def _mutate(document: SettingsDocument) -> SettingsDocument:
            return _replace(context_window_tokens=value)(document)

        return self.update(_mutate)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _read_document(self) -> SettingsDocument:
        if not self.path.is_file():
            return _default_document()
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError:
            raise MutationError("settings.json is unreadable", status=503)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MutationError(
                "settings.json is not valid JSON. Fix the file or restore it before mutating settings.",
                status=409,
            ) from exc
        if not isinstance(payload, dict):
            raise MutationError(
                "settings.json must be a JSON object. Fix the file or restore it before mutating settings.",
                status=409,
            )
        if "schemaVersion" in payload:
            schema_version = payload["schemaVersion"]
            if isinstance(schema_version, bool) or not isinstance(schema_version, int):
                raise MutationError(
                    "settings.json schemaVersion must be an integer. Fix the file or restore it before mutating settings.",
                    status=409,
                )
            if schema_version > CURRENT_SCHEMA_VERSION:
                raise MutationError(
                    "settings.json was written by a newer version of skill-manager. Update before mutating settings.",
                    status=409,
                )
        return _coerce_document(payload, _default_document())

    def _read_document_unlocked(self) -> SettingsDocument:
        if not self.path.is_file():
            return _default_document()
        raw = self.path.read_text(encoding="utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise _MutationAbort(
                MutationError(
                    "settings.json is not valid JSON. Fix the file or restore it before mutating settings.",
                    status=409,
                )
            ) from exc
        if not isinstance(payload, dict):
            raise _MutationAbort(
                MutationError(
                    "settings.json must be a JSON object. Fix the file or restore it before mutating settings.",
                    status=409,
                )
            )
        if "schemaVersion" in payload:
            schema_version = payload["schemaVersion"]
            if isinstance(schema_version, bool) or not isinstance(schema_version, int):
                raise _MutationAbort(
                    MutationError(
                        "settings.json schemaVersion must be an integer. Fix the file or restore it before mutating settings.",
                        status=409,
                    )
                )
            if schema_version > CURRENT_SCHEMA_VERSION:
                raise _MutationAbort(
                    MutationError(
                        "settings.json was written by a newer version of skill-manager. Update before mutating settings.",
                        status=409,
                    )
                )
        return _coerce_document(payload, _default_document())

    def _write_document_unlocked(self, document: SettingsDocument) -> None:
        serialized = json.dumps(_document_to_payload(document), indent=2, sort_keys=True) + "\n"
        atomic_write_text(self.path, serialized)


class _MutationAbort(Exception):
    def __init__(self, error: MutationError) -> None:
        self.error = error
        super().__init__(str(error))


def _default_document() -> SettingsDocument:
    return SettingsDocument(
        schema_version=CURRENT_SCHEMA_VERSION,
        context_window_tokens=DEFAULT_CONTEXT_WINDOW_TOKENS,
        disabled_harnesses=(),
        extra={},
    )


def _coerce_document(value: Any, fallback: SettingsDocument) -> SettingsDocument:
    if isinstance(value, SettingsDocument):
        return value
    if not isinstance(value, dict):
        raise MutationError("settings document must be a JSON object", status=409)

    if "schemaVersion" in value:
        schema_version = value["schemaVersion"]
        if isinstance(schema_version, bool) or not isinstance(schema_version, int):
            raise MutationError("settings document schemaVersion must be an integer", status=409)
    else:
        schema_version = LEGACY_SCHEMA_VERSION

    context_window = value.get("contextWindowTokens", fallback.context_window_tokens)
    if isinstance(context_window, bool) or not isinstance(context_window, int):
        context_window = fallback.context_window_tokens
    if context_window <= 0:
        context_window = fallback.context_window_tokens

    disabled = value.get("disabledHarnesses", fallback.disabled_harnesses)
    disabled_values = _normalise_disabled(disabled)

    extras = {
        str(key): value[key]
        for key in value.keys()
        if key
        not in {
            "schemaVersion",
            "contextWindowTokens",
            "disabledHarnesses",
        }
    }
    return SettingsDocument(
        schema_version=schema_version,
        context_window_tokens=context_window,
        disabled_harnesses=disabled_values,
        extra=extras,
    )


def _normalise_disabled(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    cleaned = {item for item in value if isinstance(item, str) and item}
    return tuple(sorted(cleaned))


def _validate_document(document: SettingsDocument) -> None:
    if document.schema_version > CURRENT_SCHEMA_VERSION:
        raise MutationError(
            "settings.json was written by a newer version of skill-manager. Update before mutating settings.",
            status=409,
        )
    if document.context_window_tokens <= 0:
        raise MutationError("contextWindowTokens must be a positive integer", status=409)


def _toggle_harness(document: SettingsDocument, harness: str, enabled: bool) -> SettingsDocument:
    disabled = set(document.disabled_harnesses)
    if enabled:
        disabled.discard(harness)
    else:
        disabled.add(harness)
    return SettingsDocument(
        schema_version=document.schema_version,
        context_window_tokens=document.context_window_tokens,
        disabled_harnesses=tuple(sorted(disabled)),
        extra=dict(document.extra),
    )


def _replace(**fields: Any):
    def _apply(document: SettingsDocument) -> SettingsDocument:
        merged = {
            "schemaVersion": fields.get("schema_version", document.schema_version),
            "contextWindowTokens": fields.get("context_window_tokens", document.context_window_tokens),
            "disabledHarnesses": list(fields.get("disabled_harnesses", document.disabled_harnesses)),
        }
        for key, value in document.extra.items():
            merged.setdefault(key, value)
        return _coerce_document(merged, document)

    return _apply


def _document_to_payload(document: SettingsDocument) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schemaVersion": document.schema_version,
        "contextWindowTokens": document.context_window_tokens,
        "disabledHarnesses": list(document.disabled_harnesses),
    }
    for key, value in document.extra.items():
        if key in payload:
            continue
        payload[key] = value
    return payload