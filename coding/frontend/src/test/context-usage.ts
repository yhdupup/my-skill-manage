import type { SkillContextUsage, SkillContextStatus } from "../features/skills/api/types";

/**
 * Convenience helper for tests that build Skill rows / details and need a
 * matching `contextUsage` payload. Defaults to a normal, low-usage state.
 */
export function buildContextUsage(
  usagePercent: number | null,
  options: {
    status?: SkillContextStatus;
    tokens?: number | null;
    reason?: string | null;
    window?: number;
  } = {},
): SkillContextUsage {
  const status: SkillContextStatus = options.status ?? (usagePercent === null ? "unavailable" : "normal");
  const tokens = options.tokens === undefined
    ? status === "unavailable"
      ? null
      : Math.max(1, Math.round((usagePercent ?? 0) * 1280))
    : options.tokens;
  return {
    estimatedTokens: tokens,
    contextWindowTokens: options.window ?? 128000,
    usagePercent: status === "unavailable" ? null : usagePercent,
    status,
    reason: options.reason ?? null,
  };
}