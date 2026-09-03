import { fetchJson, putJson } from "../../../api/http";
import type {
  ContextWindowTokens,
  SetContextWindowRequest,
  SetContextWindowResponse,
  SetHarnessSupportRequest,
  SettingsData,
} from "./types";

export async function fetchSettings(): Promise<SettingsData> {
  return fetchJson<SettingsData>("/settings");
}

export async function updateHarnessSupport(harness: string, enabled: boolean): Promise<{ ok: boolean; enabled: boolean }> {
  const body: SetHarnessSupportRequest = { enabled };
  return putJson<{ ok: boolean; enabled: boolean }>(
    `/settings/harnesses/${encodeURIComponent(harness)}/support`,
    body,
  );
}

export async function updateContextWindow(value: ContextWindowTokens): Promise<SetContextWindowResponse> {
  const body: SetContextWindowRequest = { contextWindowTokens: value };
  return putJson<SetContextWindowResponse>("/settings/context-window", body);
}
