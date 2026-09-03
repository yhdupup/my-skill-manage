import { describe, expect, it } from "vitest";

import type { SkillContextUsage, SkillTableRowDto } from "../api/types";

import { sortSkillRowsByUsage, sortSkillsByUsage } from "./sort-by-usage";

function usage(usagePercent: number | null, status: SkillContextUsage["status"]): SkillContextUsage {
  return {
    estimatedTokens: status === "unavailable" ? null : Math.round((usagePercent ?? 0) * 10),
    contextWindowTokens: 128000,
    usagePercent,
    status,
    reason: null,
  };
}

function row(skillRef: string, ctx: SkillContextUsage): SkillTableRowDto {
  return {
    skillRef,
    name: skillRef,
    description: "",
    displayStatus: "Unmanaged",
    actions: { canManage: false, canStopManaging: false, canDelete: false },
    cells: [],
    contextUsage: ctx,
  };
}

describe("sortSkillsByUsage", () => {
  it("sorts available rows by usagePercent descending", () => {
    const rows = [
      row("a", usage(1.0, "normal")),
      row("b", usage(5.0, "high")),
      row("c", usage(3.0, "warning")),
      row("d", usage(0.5, "normal")),
    ];
    const sorted = sortSkillsByUsage(rows);
    expect(sorted.map((r) => r.skillRef)).toEqual(["b", "c", "a", "d"]);
  });

  it("returns an empty array when given an empty array", () => {
    expect(sortSkillsByUsage([])).toEqual([]);
  });

  it("keeps all-unavailable rows in input order", () => {
    const rows = [
      row("a", usage(null, "unavailable")),
      row("b", usage(null, "unavailable")),
      row("c", usage(null, "unavailable")),
    ];
    const sorted = sortSkillsByUsage(rows);
    expect(sorted.map((r) => r.skillRef)).toEqual(["a", "b", "c"]);
  });

  it("appends unavailable rows to the end while preserving their order", () => {
    const rows = [
      row("a", usage(1.0, "normal")),
      row("u1", usage(null, "unavailable")),
      row("b", usage(5.0, "high")),
      row("u2", usage(null, "unavailable")),
      row("c", usage(3.0, "warning")),
    ];
    const sorted = sortSkillsByUsage(rows);
    expect(sorted.map((r) => r.skillRef)).toEqual(["b", "c", "a", "u1", "u2"]);
  });

  it("preserves input order when percentages tie", () => {
    const rows = [
      row("a", usage(2.0, "warning")),
      row("b", usage(2.0, "warning")),
      row("c", usage(2.0, "warning")),
    ];
    const sorted = sortSkillsByUsage(rows);
    expect(sorted.map((r) => r.skillRef)).toEqual(["a", "b", "c"]);
  });

  it("treats null usagePercent on non-unavailable status as unavailable", () => {
    const rows = [
      row("a", usage(null, "normal")),
      row("b", usage(2.0, "warning")),
    ];
    const sorted = sortSkillsByUsage(rows);
    expect(sorted.map((r) => r.skillRef)).toEqual(["b", "a"]);
  });

  it("does not mutate the input array", () => {
    const rows = [
      row("a", usage(1.0, "normal")),
      row("b", usage(5.0, "high")),
      row("u", usage(null, "unavailable")),
    ];
    const snapshot = rows.map((r) => r.skillRef);
    sortSkillsByUsage(rows);
    expect(rows.map((r) => r.skillRef)).toEqual(snapshot);
  });

  it("is idempotent for the same input", () => {
    const rows = [
      row("a", usage(1.0, "normal")),
      row("b", usage(5.0, "high")),
      row("c", usage(3.0, "warning")),
      row("u", usage(null, "unavailable")),
    ];
    const first = sortSkillsByUsage(rows).map((r) => r.skillRef);
    const second = sortSkillsByUsage(rows).map((r) => r.skillRef);
    expect(first).toEqual(second);
  });

  it("returns a new array reference on every call", () => {
    const rows = [row("a", usage(1.0, "normal"))];
    const first = sortSkillsByUsage(rows);
    const second = sortSkillsByUsage(rows);
    expect(first).not.toBe(second);
    expect(first).not.toBe(rows);
  });

  it("sortSkillRowsByUsage matches sortSkillsByUsage for SkillTableRowDto", () => {
    const rows = [
      row("a", usage(1.0, "normal")),
      row("b", usage(5.0, "high")),
      row("u", usage(null, "unavailable")),
    ];
    const expected = sortSkillsByUsage(rows).map((r) => r.skillRef);
    expect(sortSkillRowsByUsage(rows).map((r) => r.skillRef)).toEqual(expected);
  });
});