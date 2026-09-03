import { LoadingSpinner } from "../../../../components/LoadingSpinner";
import { useSkillsCopy } from "../../i18n";
import type { SkillUpdateStatus } from "../../model/types";

interface SkillDetailUpdateControlProps {
  updateStatus: SkillUpdateStatus;
  pending: boolean;
  disabled: boolean;
  onUpdate: () => void;
}

export function SkillDetailUpdateControl({
  updateStatus,
  pending,
  disabled,
  onUpdate,
}: SkillDetailUpdateControlProps) {
  const copy = useSkillsCopy();

  if (updateStatus === "update_available") {
    return (
      <button
        type="button"
        className="action-pill action-pill--md skill-detail__update-control"
        disabled={disabled}
        onClick={onUpdate}
      >
        {pending ? <LoadingSpinner size="sm" label={copy.detail.updatingSkill} /> : null}
        {copy.detail.updateAvailable}
      </button>
    );
  }

  if (updateStatus === "local_changes_detected") {
    return null;
  }

  const label = updateStatus === "no_update_available"
    ? copy.detail.noUpdateAvailable
    : copy.detail.noSourceAvailable;

  return (
    <span className="card-status-pill card-status-pill--md skill-detail__update-control">
      {label}
    </span>
  );
}