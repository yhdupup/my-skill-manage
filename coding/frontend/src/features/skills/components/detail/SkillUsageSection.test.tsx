import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buildContextUsage } from "../../../../test/context-usage";
import type { SkillDetail } from "../../model/types";
import { SkillUsageSection } from "./SkillUsageSection";

function makeDetail(contextUsage = buildContextUsage(1.5)): SkillDetail {
  return {
    skillRef: "shared:demo",
    name: "Demo",
    description: "Demo detail",
    displayStatus: "Managed",
    attentionMessage: null,
    actions: {
      canManage: false,
      updateStatus: null,
      stopManagingStatus: null,
      stopManagingHarnessLabels: [],
      canDelete: false,
      deleteHarnessLabels: [],
    },
    harnessCells: [],
    locations: [],
    sourceLinks: null,
    documentMarkdown: null,
    contextUsage,
  };
}

describe("SkillUsageSection", () => {
  it("renders the UsageCell for a normal status", () => {
    render(<SkillUsageSection detail={makeDetail()} />);
    expect(screen.getByRole("status").className).toContain("usage-cell--normal");
  });

  it("renders the unavailable label without rendering the reason", () => {
    render(
      <SkillUsageSection
        detail={makeDetail(
          buildContextUsage(null, {
            status: "unavailable",
            reason: "skill_document_unreadable",
          }),
        )}
      />,
    );
    expect(screen.getByText(/此 Skill 当前无法估算上下文占用/)).toBeInTheDocument();
    expect(screen.queryByText(/skill_document_unreadable/)).not.toBeInTheDocument();
  });
});