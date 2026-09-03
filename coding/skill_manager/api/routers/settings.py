from __future__ import annotations

from fastapi import APIRouter, Depends

from skill_manager.application import BackendContainer
from skill_manager.api.deps import get_container
from skill_manager.api.schemas import (
    SetContextWindowRequest,
    SetContextWindowResponse,
    SetHarnessSupportRequest,
    SettingsResponse,
)

router = APIRouter(prefix="/api/settings")


@router.get("", response_model=SettingsResponse)
def settings(container: BackendContainer = Depends(get_container)) -> dict[str, object]:
    return container.settings_queries.get_settings()


@router.put("/harnesses/{harness}/support")
def set_harness_support(
    harness: str,
    body: SetHarnessSupportRequest,
    container: BackendContainer = Depends(get_container),
) -> dict[str, object]:
    return container.settings_mutations.set_harness_support(harness, body.enabled)


@router.put("/context-window", response_model=SetContextWindowResponse)
def set_context_window(
    body: SetContextWindowRequest,
    container: BackendContainer = Depends(get_container),
) -> dict[str, object]:
    result = container.settings_mutations.set_context_window_tokens(body.contextWindowTokens)
    return {"ok": True, "contextWindowTokens": result["contextWindowTokens"]}