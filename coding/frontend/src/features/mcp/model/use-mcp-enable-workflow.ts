import { useCallback } from "react";

import type { McpInventoryEntryDto, McpServerDetailDto } from "../api/management-types";
import type { McpInstallConfigValues } from "./install-config";
import { useMcpEnableConfigGate } from "./use-mcp-enable-config-gate";

type EnableEntry = Pick<
  McpInventoryEntryDto | McpServerDetailDto,
  "displayName" | "installConfigStatus" | "spec"
>;

interface UseMcpEnableWorkflowParams {
  loadErrorMessage: string;
  bulkRequiresSingleMessage?: (displayName: string) => string;
}

export function useMcpEnableWorkflow({
  loadErrorMessage,
  bulkRequiresSingleMessage,
}: UseMcpEnableWorkflowParams) {
  const configGate = useMcpEnableConfigGate({ loadErrorMessage });

  const requestEnable = useCallback(
    (
      entry: EnableEntry,
      targetLabel: string,
      onProceed: (config?: McpInstallConfigValues) => void,
    ): void => {
      configGate.requestEnable({
        spec: entry.spec ?? null,
        displayName: entry.displayName,
        targetLabel,
        installConfigStatus: entry.installConfigStatus,
        onProceed,
      });
    },
    [configGate],
  );

  const requestBulkEnable = useCallback(
    async (
      entries: readonly McpInventoryEntryDto[],
      onSingleEntry: (entry: McpInventoryEntryDto) => void,
      onManyEntries: () => Promise<void>,
      onBlocked: (message: string) => void,
    ): Promise<void> => {
      if (entries.length === 0) return;
      if (entries.length === 1) {
        onSingleEntry(entries[0]);
        return;
      }
      const blocked = entries.find((entry) => entry.installConfigStatus.missingRequired.length > 0);
      if (blocked) {
        onBlocked(bulkRequiresSingleMessage?.(blocked.displayName) ?? blocked.displayName);
        return;
      }
      await onManyEntries();
    },
    [bulkRequiresSingleMessage],
  );

  return {
    requestEnable,
    requestBulkEnable,
    pendingConfig: configGate.pendingConfig,
    cancelConfig: configGate.cancelConfig,
    submitConfig: configGate.submitConfig,
    configError: configGate.configError,
  };
}
