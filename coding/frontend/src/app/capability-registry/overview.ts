import type { QueryClient } from "@tanstack/react-query";
import { useMemo } from "react";

import {
  invalidateSkillsQueries,
  useSkillsListQuery,
  type HarnessCell,
  type SkillContextUsage,
  type SkillsWorkspaceData,
} from "../../features/skills/public";
import { overviewCopy, useOverviewCopy, type OverviewCopy } from "../../features/overview/public";
import { skillStatusConcept } from "../../lib/product-language";

export interface OverviewStatMetric {
  value: number | null;
  detail: string;
}

export interface OverviewStats {
  inUse: OverviewStatMetric;
  enabledBindings: OverviewStatMetric;
}

export interface OverviewSkillRow {
  skillRef: string;
  name: string;
  description: string;
  contextUsage: SkillContextUsage;
  harnessCells: HarnessCell[];
}

export interface OverviewModel {
  stats: OverviewStats;
  skillRows: OverviewSkillRow[];
}

export function useOverviewData() {
  const skillsQuery = useSkillsListQuery();
  const model = useOverviewModel(skillsQuery.data);
  return {
    skillsQuery,
    model,
  };
}

export async function invalidateOverviewData(queryClient: QueryClient): Promise<void> {
  await invalidateSkillsQueries(queryClient);
}

export function useOverviewModel(
  skills: SkillsWorkspaceData | null | undefined,
): OverviewModel {
  const copy = useOverviewCopy();
  return useMemo(() => buildOverviewModel(skills, copy), [skills, copy]);
}

export function buildOverviewModel(
  skills: SkillsWorkspaceData | null | undefined,
  copy: OverviewCopy = overviewCopy.en,
): OverviewModel {
  const skillRows = buildSkillRows(skills);
  const enabledBindings = skills
    ? skillRows.reduce(
        (total, row) => total + row.harnessCells.filter((cell) => cell.state === "enabled").length,
        0,
      )
    : null;
  return {
    stats: buildStats({
      inUseSkills: skills ? skillRows.length : null,
      enabledBindings,
      copy,
    }),
    skillRows,
  };
}

function buildStats({
  inUseSkills,
  enabledBindings,
  copy,
}: {
  inUseSkills: number | null;
  enabledBindings: number | null;
  copy: OverviewCopy;
}): OverviewStats {
  return {
    inUse: {
      value: inUseSkills,
      detail: copy.stats.inUseDetail,
    },
    enabledBindings: {
      value: enabledBindings,
      detail: copy.stats.enabledBindingsDetail,
    },
  };
}

function buildSkillRows(skills: SkillsWorkspaceData | null | undefined): OverviewSkillRow[] {
  if (!skills) return [];

  const installedHarnesses = new Set(
    skills.harnessColumns
      .filter((column) => column.installed)
      .map((column) => column.harness),
  );

  return skills.rows
    .filter((row) => skillStatusConcept(row.displayStatus) === "inUse")
    .map((row) => ({
      skillRef: row.skillRef,
      name: row.name,
      description: row.description,
      contextUsage: row.contextUsage,
      harnessCells: row.cells.filter((cell) => installedHarnesses.has(cell.harness)),
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}
