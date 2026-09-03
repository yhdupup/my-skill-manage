import { useState } from "react";

import { ErrorBanner } from "../../../components/ErrorBanner";
import { useOverviewData, type OverviewSkillRow } from "../../../app/capability-registry";
import {
  pendingToggleHarnessesForSkill,
  SkillDetailModal,
  useSkillsWorkspaceController,
  useToggleSkillMutation,
  type HarnessCell,
} from "../../skills/public";
import { SkillUsageOverview, toggleKey } from "../components/SkillUsageOverview";
import { StatisticsBand } from "../components/StatisticsBand";
import { useOverviewCopy } from "../i18n";

export default function OverviewPage() {
  const { skillsQuery, model } = useOverviewData();
  const copy = useOverviewCopy();
  const toggleMutation = useToggleSkillMutation();
  const detailController = useSkillsWorkspaceController();
  const [pendingKeys, setPendingKeys] = useState<Set<string>>(() => new Set());
  const [actionError, setActionError] = useState("");

  const skillsLoading = skillsQuery.isPending && !skillsQuery.data;
  const loading = skillsLoading;
  const selectedPendingToggleHarnesses = detailController.selectedSkillRef
    ? pendingToggleHarnessesForSkill(
        detailController.context.pendingToggleKeys,
        detailController.selectedSkillRef,
      )
    : EMPTY_PENDING_TOGGLE_HARNESSES;
  const selectedPendingStructuralAction = detailController.selectedSkillRef
    ? detailController.context.pendingStructuralActions.get(detailController.selectedSkillRef) ?? null
    : null;

  async function handleToggle(row: OverviewSkillRow, cell: HarnessCell): Promise<void> {
    if (!cell.interactive) return;
    const key = toggleKey(row.skillRef, cell.harness);
    setActionError("");
    setPendingKeys((current) => new Set(current).add(key));
    try {
      await toggleMutation.mutateAsync({
        skillRef: row.skillRef,
        harness: cell.harness,
        nextState: cell.state === "enabled" ? "disabled" : "enabled",
      });
    } catch (error) {
      setActionError(errorMessage(error));
    } finally {
      setPendingKeys((current) => {
        const next = new Set(current);
        next.delete(key);
        return next;
      });
    }
  }

  return (
    <>
      <header className="overview-hero">
        <div className="overview-hero__copy">
          <span className="overview-hero__eyebrow">{copy.screen.eyebrow}</span>
          <h1 className="overview-hero__title">
            <span>{copy.screen.titlePrimary}</span>
            <span>{copy.screen.titleSecondary}</span>
          </h1>
          <p>{copy.screen.subtitle}</p>
        </div>
        <StatisticsBand stats={model.stats} loading={loading} />
      </header>

      <div className="overview-page">
        {skillsQuery.isError && !skillsQuery.data ? (
          <ErrorBanner message={copy.screen.unableToLoadSkills(errorMessage(skillsQuery.error))} />
        ) : null}
        {actionError ? <ErrorBanner message={actionError} onDismiss={() => setActionError("")} /> : null}
        {detailController.actionErrorMessage ? (
          <ErrorBanner
            message={detailController.actionErrorMessage}
            onDismiss={detailController.dismissActionError}
          />
        ) : null}

        <SkillUsageOverview
          rows={model.skillRows}
          loading={loading}
          pendingKeys={pendingKeys}
          onToggle={(row, cell) => void handleToggle(row, cell)}
        />
      </div>

      <SkillDetailModal
        open={Boolean(detailController.selectedSkillRef)}
        skillRef={detailController.selectedSkillRef}
        pendingToggleHarnesses={selectedPendingToggleHarnesses}
        pendingStructuralAction={selectedPendingStructuralAction}
        onClose={detailController.closeSelectedSkill}
        onManageSkill={detailController.handleManageSkill}
        onToggleSkill={detailController.handleToggleSkill}
        onUpdateSkill={detailController.handleUpdateSkill}
        onRemoveSkill={detailController.handleRemoveSkill}
        onDeleteSkill={detailController.handleDeleteSkill}
      />
    </>
  );
}

const EMPTY_PENDING_TOGGLE_HARNESSES = new Set<string>();

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unknown error";
}
