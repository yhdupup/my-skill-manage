from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class SettingsStorageResponse(BaseModel):
    platform: Literal["macos", "linux", "windows"]
    configDir: str
    dataDir: str
    stateDir: str
    skillsStorePath: str
    marketplaceCachePath: str
    settingsPath: str


class SettingsHarnessResponse(BaseModel):
    harness: str
    label: str
    logoKey: str | None = None
    supportEnabled: bool
    installed: bool
    managedLocation: str | None


class SettingsResponse(BaseModel):
    contextWindowTokens: int
    storage: SettingsStorageResponse
    harnesses: list[SettingsHarnessResponse]


class SetContextWindowRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contextWindowTokens: StrictInt = Field(..., gt=0)


class SetContextWindowResponse(BaseModel):
    ok: Literal[True]
    contextWindowTokens: int


__all__ = [
    "SetContextWindowRequest",
    "SetContextWindowResponse",
    "SettingsHarnessResponse",
    "SettingsResponse",
    "SettingsStorageResponse",
]