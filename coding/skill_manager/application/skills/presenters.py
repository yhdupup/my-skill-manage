from __future__ import annotations

from skill_manager.application.skills.context_estimator import SkillContextUsage, SkillContextEstimator

from .inventory import InventoryColumn, InventoryEntry, InventorySighting, SkillInventory
from .policy import (
    attention_message,
    can_delete,
    can_manage,
    cell_state,
    display_status,
    stop_managing_status,
)


def skills_page_payload(
    inventory: SkillInventory,
    *,
    context_estimator: SkillContextEstimator,
    context_window_tokens: int,
) -> dict[str, object]:
    counts = {
        "managed": sum(1 for entry in inventory.entries if display_status(entry) == "Managed"),
        "unmanaged": sum(1 for entry in inventory.entries if display_status(entry) == "Unmanaged"),
    }
    return {
        "summary": counts,
        "harnessColumns": [column_payload(column) for column in inventory.columns],
        "rows": [
            row_payload(entry, inventory.columns, context_estimator=context_estimator, context_window_tokens=context_window_tokens)
            for entry in inventory.entries
        ],
    }


def skill_detail_payload(
    entry: InventoryEntry,
    *,
    columns: tuple[InventoryColumn, ...],
    document_markdown: str | None,
    source_links: dict[str, str | None] | None,
    context_usage: SkillContextUsage,
) -> dict[str, object]:
    return {
        "skillRef": entry.skill_ref,
        "name": entry.name,
        "description": entry.description,
        "displayStatus": display_status(entry),
        "attentionMessage": attention_message(entry),
        "actions": {
            "canManage": can_manage(entry),
            "stopManagingStatus": stop_managing_status_payload(entry),
            "stopManagingHarnessLabels": linked_harness_labels(entry, columns),
            "canDelete": can_delete(entry),
            "deleteHarnessLabels": linked_harness_labels(entry, columns),
        },
        "harnessCells": [cell_payload(entry, column) for column in columns],
        "locations": [sighting_payload(sighting) for sighting in entry.detail_sightings()],
        "sourceLinks": source_links,
        "documentMarkdown": document_markdown,
        "contextUsage": context_usage.to_payload(),
    }


def source_status_payload(update_status: str | None) -> dict[str, object]:
    return {"updateStatus": update_status}


def column_payload(column: InventoryColumn) -> dict[str, object]:
    return {
        "harness": column.harness,
        "label": column.label,
        "logoKey": column.logo_key,
        "installed": column.installed,
    }


def row_payload(
    entry: InventoryEntry,
    columns: tuple[InventoryColumn, ...],
    *,
    context_estimator: SkillContextEstimator,
    context_window_tokens: int,
) -> dict[str, object]:
    return {
        "skillRef": entry.skill_ref,
        "name": entry.name,
        "description": entry.description,
        "displayStatus": display_status(entry),
        "actions": {
            "canManage": can_manage(entry),
            "canStopManaging": stop_managing_status(entry) == "available",
            "canDelete": can_delete(entry),
        },
        "cells": [cell_payload(entry, column) for column in columns],
        "contextUsage": context_estimator.estimate(
            _representative_skill_root(entry),
            context_window_tokens,
        ).to_payload(),
    }


def cell_payload(entry: InventoryEntry, column: InventoryColumn) -> dict[str, object]:
    state = cell_state(entry, column.harness)
    # `interactive` is the single source of truth for "this cell can be
    # flipped right now". It requires both a toggleable state and a
    # harness-specific skills capability, which may be a CLI or an app
    # installation depending on that harness. Every consumer downstream
    # (card counts, board bucketing, harness chip stack) reads
    # `interactive` and is correct for free.
    is_interactive = state in {"enabled", "disabled"} and column.installed
    return {
        "harness": column.harness,
        "label": column.label,
        "logoKey": column.logo_key,
        "state": state,
        "interactive": is_interactive,
    }


def sighting_payload(sighting: InventorySighting) -> dict[str, str | None]:
    return {
        "kind": sighting.kind,
        "harness": sighting.harness,
        "label": sighting.label,
        "scope": sighting.scope,
        "path": str(sighting.path) if sighting.path is not None else None,
        "revision": sighting.revision,
        "sourceKind": sighting.source.kind,
        "sourceLocator": sighting.source.locator,
        "detail": sighting.detail or None,
    }


def linked_harness_labels(entry: InventoryEntry, columns: tuple[InventoryColumn, ...]) -> list[str]:
    linked_harnesses = entry.linked_harnesses()
    return [column.label for column in columns if column.harness in linked_harnesses]


def stop_managing_status_payload(entry: InventoryEntry) -> str | None:
    from .policy import stop_managing_status

    return stop_managing_status(entry)


def _representative_skill_root(entry: InventoryEntry) -> "object | None":
    """Pick the canonical skill root used for context estimation.

    Preference order:

    1. The shared managed package, when available.
    2. The first ``detail_sightings`` entry that actually contains a
       ``SKILL.md``.
    3. ``None`` so the estimator emits ``unavailable`` with the
       ``skill_document_missing`` reason code.
    """

    from pathlib import Path

    if entry.package_path is not None and (entry.package_path / "SKILL.md").is_file():
        return entry.package_path
    for sighting in entry.detail_sightings():
        path = sighting.path
        if path is not None and (path / "SKILL.md").is_file():
            return path
    return None