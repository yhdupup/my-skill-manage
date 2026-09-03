import { describe, expect, it } from "vitest";

import type { SkillsWorkspaceData } from "../../features/skills/public";
import { buildOverviewModel } from "./overview";

describe("buildOverviewModel", () => {
  it("builds a skill-first overview from managed skills and installed harnesses", () => {
    const model = buildOverviewModel(workspace());

    expect(model.skillRows).toHaveLength(1);
    expect(model.skillRows[0]).toMatchObject({
      skillRef: "writer",
      name: "Writer",
      description: "Writes concise product copy.",
    });
    expect(model.skillRows[0].harnessCells.map((cell) => cell.harness)).toEqual([
      "codex",
      "trae",
    ]);
    expect(model.stats.inUse.value).toBe(1);
    expect(model.stats.enabledBindings.value).toBe(1);
  });
});

function workspace(): SkillsWorkspaceData {
  const contextUsage = {
    estimatedTokens: 3200,
    contextWindowTokens: 128000,
    usagePercent: 2.5,
    status: "normal" as const,
    reason: null,
  };
  const actions = { canManage: false, canStopManaging: true, canDelete: true };
  return {
    summary: { managed: 1, unmanaged: 1 },
    harnessColumns: [
      { harness: "codex", label: "Codex", installed: true, logoKey: "codex" },
      { harness: "trae", label: "Trae CN", installed: true, logoKey: "trae" },
      { harness: "cursor", label: "Cursor", installed: false, logoKey: "cursor" },
    ],
    rows: [
      {
        skillRef: "writer",
        name: "Writer",
        description: "Writes concise product copy.",
        displayStatus: "Managed",
        actions,
        contextUsage,
        cells: [
          { harness: "codex", label: "Codex", logoKey: "codex", state: "enabled", interactive: true },
          { harness: "trae", label: "Trae CN", logoKey: "trae", state: "disabled", interactive: true },
          { harness: "cursor", label: "Cursor", logoKey: "cursor", state: "empty", interactive: false },
        ],
      },
      {
        skillRef: "review-me",
        name: "Review me",
        description: "Not managed.",
        displayStatus: "Unmanaged",
        actions: { canManage: true, canStopManaging: false, canDelete: false },
        contextUsage,
        cells: [],
      },
    ],
  };
}
