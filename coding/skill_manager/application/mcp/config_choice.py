from __future__ import annotations

from dataclasses import dataclass

from skill_manager.errors import MutationError

from .contracts import McpHarnessScan
from .env import is_env_var_reference
from .redaction import annotate_redacted_env, redact_payload, redacted_spec_dict
from .store import McpServerSpec


@dataclass(frozen=True)
class McpConfigChoice:
    id: str
    source_kind: str
    observed_harness: str | None
    label: str
    logo_key: str | None
    config_path: str | None
    payload_preview: dict[str, object]
    spec: McpServerSpec
    env: list[dict[str, object]]
    recommended: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "sourceKind": self.source_kind,
            "observedHarness": self.observed_harness,
            "label": self.label,
            "logoKey": self.logo_key,
            "configPath": self.config_path,
            "payloadPreview": self.payload_preview,
            "spec": redacted_spec_dict(self.spec),
            "env": self.env,
            "recommended": self.recommended,
        }


def config_choices_payload(
    name: str,
    managed_spec: McpServerSpec,
    scans: tuple[McpHarnessScan, ...],
) -> list[dict[str, object]]:
    choices = _config_choices(name, managed_spec, scans)
    recommended_id = _recommended_choice_id(choices)
    return [
        (
            choice
            if choice.id != recommended_id
            else McpConfigChoice(
                id=choice.id,
                source_kind=choice.source_kind,
                observed_harness=choice.observed_harness,
                label=choice.label,
                logo_key=choice.logo_key,
                config_path=choice.config_path,
                payload_preview=choice.payload_preview,
                spec=choice.spec,
                env=choice.env,
                recommended=True,
            )
        ).to_dict()
        for choice in choices
    ]


def observed_spec_from_scans(
    name: str,
    observed_harness: str,
    scans: tuple[McpHarnessScan, ...],
) -> McpServerSpec:
    for scan in scans:
        if scan.harness != observed_harness:
            continue
        for entry in scan.entries:
            if entry.name != name:
                continue
            if entry.parsed_spec is None:
                raise MutationError(
                    entry.parse_issue or f"unable to parse '{name}' in {observed_harness}",
                    status=409,
                )
            return entry.parsed_spec
    raise MutationError(f"server '{name}' was not observed in harness '{observed_harness}'", status=404)


def recommended_observed_harness(sightings) -> str | None:
    sightings = list(sightings)
    if not sightings:
        return None

    for sighting in sightings:
        if sighting.spec.transport == "stdio" and _spec_has_env_ref(sighting.spec):
            return sighting.harness
    for sighting in sightings:
        if sighting.spec.transport == "stdio":
            return sighting.harness
    for sighting in sightings:
        if sighting.spec.transport != "stdio" and not _url_has_embedded_credential(sighting.spec.url):
            return sighting.harness
    return None


def _config_choices(
    name: str,
    managed_spec: McpServerSpec,
    scans: tuple[McpHarnessScan, ...],
) -> list[McpConfigChoice]:
    choices: list[McpConfigChoice] = [
        McpConfigChoice(
            id="managed",
            source_kind="managed",
            observed_harness=None,
            label="Managed config",
            logo_key=None,
            config_path=None,
            payload_preview=redacted_spec_dict(managed_spec),
            spec=managed_spec,
            env=annotate_redacted_env(managed_spec.env),
        )
    ]
    for scan in scans:
        for observed in scan.entries:
            if observed.name != name or observed.state != "drifted":
                continue
            if observed.parsed_spec is None:
                continue
            choices.append(
                McpConfigChoice(
                    id=f"harness:{scan.harness}",
                    source_kind="harness",
                    observed_harness=scan.harness,
                    label=f"{scan.label} config",
                    logo_key=scan.logo_key,
                    config_path=str(scan.config_path) if scan.config_present else None,
                    payload_preview=redact_payload(dict(observed.raw_payload or {})),
                    spec=observed.parsed_spec,
                    env=annotate_redacted_env(observed.parsed_spec.env),
                )
            )
    return choices


def _recommended_choice_id(choices: list[McpConfigChoice]) -> str | None:
    harness_choices = [choice for choice in choices if choice.source_kind == "harness"]
    if not harness_choices:
        return "managed" if choices else None

    def has_env_ref(choice: McpConfigChoice) -> bool:
        return any(bool(entry.get("isEnvRef")) for entry in choice.env)

    for choice in harness_choices:
        if choice.spec.transport == "stdio" and has_env_ref(choice):
            return choice.id
    for choice in harness_choices:
        if choice.spec.transport == "stdio":
            return choice.id
    for choice in harness_choices:
        if choice.spec.transport != "stdio" and not _url_has_embedded_credential(choice.spec.url):
            return choice.id
    return choices[0].id if choices else None


def _url_has_embedded_credential(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return any(token in lowered for token in ("api_key=", "api-key=", "token=", "secret=", "auth=", "authorization="))


def _spec_has_env_ref(spec: McpServerSpec) -> bool:
    return any(is_env_var_reference(value) for _key, value in spec.env or ())


__all__ = [
    "McpConfigChoice",
    "config_choices_payload",
    "observed_spec_from_scans",
    "recommended_observed_harness",
]
