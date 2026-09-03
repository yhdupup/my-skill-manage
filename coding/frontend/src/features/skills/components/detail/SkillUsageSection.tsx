import { DetailSection } from "../../../../components/detail/DetailSection";
import { useSkillsCopy } from "../../i18n";
import type { SkillDetail } from "../../model/types";
import { UsageCell } from "../cards/UsageCell";

interface SkillUsageSectionProps {
  detail: SkillDetail;
}

export function SkillUsageSection({ detail }: SkillUsageSectionProps) {
  const copy = useSkillsCopy();
  const usage = detail.contextUsage;
  const isUnavailable =
    usage.status === "unavailable" || usage.usagePercent === null;

  return (
    <DetailSection heading={copy.usage.detailHeading}>
      {isUnavailable ? (
        <p
          className="muted-text"
          role="status"
          aria-label={copy.usage.ariaStatus("unavailable")}
        >
          {copy.usage.detailUnavailable}
        </p>
      ) : (
        <UsageCell contextUsage={usage} />
      )}
    </DetailSection>
  );
}
