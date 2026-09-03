import { useMemo } from "react";

import { UiTooltip } from "../../../../components/ui/UiTooltip";
import type { SkillContextUsage, SkillContextStatus } from "../../api/types";
import { useSkillsCopy } from "../../i18n";

interface UsageCellProps {
  contextUsage: SkillContextUsage;
}

interface DisplayModel {
  text: string;
  ariaStatus: SkillContextStatus;
  tooltip: string;
}

function buildDisplay(
  usage: SkillContextUsage,
  copy: ReturnType<typeof useSkillsCopy>,
): DisplayModel {
  const status = usage.status;
  if (status === "unavailable" || usage.usagePercent === null) {
    return {
      text: copy.usage.unavailable,
      ariaStatus: "unavailable",
      tooltip: copy.usage.tooltip,
    };
  }

  const text = copy.usage.formatPercent(usage.usagePercent);
  return {
    text,
    ariaStatus: status,
    tooltip: copy.usage.tooltip,
  };
}

export function UsageCell({ contextUsage }: UsageCellProps) {
  const copy = useSkillsCopy();
  const model = useMemo(() => buildDisplay(contextUsage, copy), [contextUsage, copy]);

  return (
    <UiTooltip content={model.tooltip}>
      <span
        className={`usage-cell usage-cell--${model.ariaStatus}`}
        role="status"
        aria-label={copy.usage.ariaSummary(model.text)}
      >
        {model.text}
      </span>
    </UiTooltip>
  );
}
