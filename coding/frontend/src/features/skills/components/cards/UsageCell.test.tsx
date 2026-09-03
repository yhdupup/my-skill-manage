import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SkillContextUsage } from "../../api/types";
import { UsageCell } from "./UsageCell";

function makeUsage(overrides: Partial<SkillContextUsage> = {}): SkillContextUsage {
  return {
    estimatedTokens: 2400,
    contextWindowTokens: 128000,
    usagePercent: 1.88,
    status: "normal",
    reason: null,
    ...overrides,
  };
}

describe("UsageCell", () => {
  it("renders percentage without an estimated Token field for a normal skill", () => {
    render(<UsageCell contextUsage={makeUsage()} />);
    expect(screen.getByText(/1\.88%/)).toBeInTheDocument();
    expect(screen.queryByText(/Token/)).not.toBeInTheDocument();
  });

  it("renders warning copy with status role when status is warning", () => {
    render(
      <UsageCell
        contextUsage={makeUsage({ status: "warning", usagePercent: 3.5, estimatedTokens: 4480 })}
      />,
    );
    const cell = screen.getByRole("status");
    expect(cell.className).toContain("usage-cell--warning");
    expect(cell.getAttribute("aria-label")).toMatch(/预计上下文/);
    expect(cell.textContent).toMatch(/3\.50%/);
  });

  it("renders high usage copy and uses the danger tone", () => {
    render(
      <UsageCell
        contextUsage={makeUsage({ status: "high", usagePercent: 6.7, estimatedTokens: 8600 })}
      />,
    );
    const cell = screen.getByRole("status");
    expect(cell.className).toContain("usage-cell--high");
    expect(cell.textContent).toMatch(/6\.70%/);
  });

  it("renders the unavailable label and hides percentage when status is unavailable", () => {
    render(
      <UsageCell
        contextUsage={makeUsage({ status: "unavailable", estimatedTokens: null, usagePercent: null, reason: "skill_document_missing" })}
      />,
    );
    const cell = screen.getByRole("status");
    expect(cell.className).toContain("usage-cell--unavailable");
    expect(cell.textContent).toMatch(/无法估算/);
    expect(cell.textContent).not.toMatch(/%/);
    expect(cell.textContent).not.toContain("skill_document_missing");
  });

  it("renders the unavailable label when percentage is null even with normal status", () => {
    render(
      <UsageCell
        contextUsage={makeUsage({ estimatedTokens: null, usagePercent: null })}
      />,
    );
    expect(screen.getByRole("status").className).toContain("usage-cell--unavailable");
  });

  it("ignores Token estimates and renders only the context percentage", () => {
    render(<UsageCell contextUsage={makeUsage({ estimatedTokens: 480, usagePercent: 0.38 })} />);
    expect(screen.getByText("0.38%")).toBeInTheDocument();
    expect(screen.queryByText(/Token/)).not.toBeInTheDocument();
  });
});
