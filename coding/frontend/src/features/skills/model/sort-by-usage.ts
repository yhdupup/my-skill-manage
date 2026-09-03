import type { SkillContextUsage } from "../api/types";
import type { SkillTableRowDto } from "../api/types";

/**
 * Sortable view of a Skill row.
 *
 * The sort only consults `contextUsage`. Rows that report `unavailable`
 * (typically because the `SKILL.md` is missing, unreadable or the
 * reference window is invalid) keep their original position so the UI
 * can decide separately how to display them.
 */
export type SortableSkillRow = {
  contextUsage: Pick<SkillContextUsage, "usagePercent" | "status">;
};

type SortableStatus = SortableSkillRow["contextUsage"]["status"];

/**
 * Stable sort rows by `contextUsage`.
 *
 * Rules:
 *
 * 1. `unavailable` rows are moved to the end of the result while keeping
 *    their relative input order (stable sort).
 * 2. Other rows (`normal` | `warning` | `high`) are sorted by
 *    `usagePercent` descending. Ties preserve the input order.
 * 3. A row that claims a non-`unavailable` status but provides a
 *    `null` `usagePercent` falls back to the `unavailable` bucket.
 *    This guards against unexpected backends and keeps the function
 *    total over `SkillTableRowDto[]`.
 * 4. The input array is not mutated; a new array is returned.
 * 5. The function is pure: same input => same output, no side effects.
 */
export function sortSkillsByUsage<T extends SortableSkillRow>(rows: readonly T[]): T[] {
  const sortable: T[] = [];
  const unavailable: T[] = [];

  for (const row of rows) {
    if (isUnavailable(row.contextUsage)) {
      unavailable.push(row);
    } else {
      sortable.push(row);
    }
  }

  sortable.sort((left, right) => {
    const leftPercent = left.contextUsage.usagePercent ?? 0;
    const rightPercent = right.contextUsage.usagePercent ?? 0;
    if (leftPercent === rightPercent) {
      return 0;
    }
    // Descending by usagePercent; let Array.prototype.sort handle stability.
    return rightPercent - leftPercent;
  });

  return sortable.concat(unavailable);
}

function isUnavailable(usage: SortableSkillRow["contextUsage"]): boolean {
  if (usage.status === ("unavailable" satisfies SortableStatus)) {
    return true;
  }
  if (usage.usagePercent === null || usage.usagePercent === undefined) {
    return true;
  }
  return false;
}

/**
 * Convenience wrapper around {@link sortSkillsByUsage} for the most common
 * call site: a skills list payload coming from the backend.
 */
export function sortSkillRowsByUsage(rows: readonly SkillTableRowDto[]): SkillTableRowDto[] {
  return sortSkillsByUsage(rows);
}