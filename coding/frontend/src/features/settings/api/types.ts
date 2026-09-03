import type { components } from "../../../api/generated";

export type SetHarnessSupportRequest = components["schemas"]["SetHarnessSupportRequest"];
export type SetContextWindowRequest = components["schemas"]["SetContextWindowRequest"];
export type SetContextWindowResponse = components["schemas"]["SetContextWindowResponse"];
export type SettingsData = components["schemas"]["SettingsResponse"];
export type SettingsHarness = components["schemas"]["SettingsHarnessResponse"];

export type ContextWindowTokens = SettingsData["contextWindowTokens"];
