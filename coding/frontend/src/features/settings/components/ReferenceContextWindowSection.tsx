import { useEffect, useId, useMemo, useState } from "react";

import { useToast } from "../../../components/Toast";
import { UiTooltip } from "../../../components/ui/UiTooltip";
import { useContextWindowMutation, useContextWindowQuery } from "../api/queries";
import type { SettingsCopy } from "../i18n";

interface ReferenceContextWindowSectionProps {
  copy: SettingsCopy["referenceContextWindow"];
  unableToUpdateMessage: string;
}

const SAVED_FEEDBACK_TIMEOUT_MS = 1500;

const STRICT_POSITIVE_INTEGER = /^[1-9]\d*$/;

function sanitizeInput(raw: string): string {
  // Keep digits only; the layout avoids decimals, signs and whitespace so the
  // user cannot enter invalid values via keyboard.
  return raw.replace(/[^\d]/g, "");
}

function parsePositiveInteger(raw: string): number | null {
  if (!STRICT_POSITIVE_INTEGER.test(raw)) {
    return null;
  }
  const value = Number.parseInt(raw, 10);
  if (!Number.isFinite(value) || value <= 0) {
    return null;
  }
  return value;
}

export function ReferenceContextWindowSection({
  copy,
  unableToUpdateMessage,
}: ReferenceContextWindowSectionProps) {
  const inputId = useId();
  const query = useContextWindowQuery();
  const mutation = useContextWindowMutation();
  const { toast } = useToast();

  const currentValue = query.data;
  const [draft, setDraft] = useState<string>(() =>
    currentValue === undefined ? "" : String(currentValue),
  );
  const [savedFeedback, setSavedFeedback] = useState(false);

  useEffect(() => {
    if (currentValue === undefined) {
      return;
    }
    if (mutation.isPending) {
      return;
    }
    // Only sync from server when the user is not actively editing.
    setDraft((previous) => (previous === "" ? String(currentValue) : previous));
  }, [currentValue, mutation.isPending]);

  useEffect(() => {
    if (!savedFeedback) {
      return;
    }
    const timer = window.setTimeout(() => {
      setSavedFeedback(false);
    }, SAVED_FEEDBACK_TIMEOUT_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, [savedFeedback]);

  const parsed = useMemo(() => parsePositiveInteger(draft), [draft]);
  const isDirty = currentValue !== undefined && parsed !== null && parsed !== currentValue;
  const isInvalid = draft.length > 0 && parsed === null;
  const isSaveDisabled = !isDirty || mutation.isPending;

  function handleChange(next: string): void {
    setSavedFeedback(false);
    setDraft(sanitizeInput(next));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (parsed === null || !isDirty) {
      return;
    }
    try {
      await mutation.mutateAsync(parsed);
      setSavedFeedback(true);
    } catch (error) {
      toast(error instanceof Error ? error.message : unableToUpdateMessage);
    }
  }

  return (
    <form className="settings-row settings-row--reference-window" onSubmit={handleSubmit}>
      <span className="settings-row__icon" aria-hidden="true">W</span>
      <div className="settings-row__body">
        <label htmlFor={inputId} className="settings-row__title">
          {copy.label}
        </label>
        <p className="settings-row__sub">{copy.description}</p>
        {isInvalid ? (
          <p className="settings-row__error" role="alert">
            {copy.invalidPositiveInteger}
          </p>
        ) : null}
      </div>
      <div className="settings-row__controls settings-row__controls--reference-window">
        <UiTooltip content={copy.tooltip}>
          <input
            id={inputId}
            type="text"
            inputMode="numeric"
            className="settings-row__input"
            value={draft}
            placeholder={copy.placeholder}
            aria-describedby={`${inputId}-hint`}
            aria-invalid={isInvalid}
            onChange={(event) => handleChange(event.target.value)}
            disabled={query.isLoading}
          />
        </UiTooltip>
        <button
          type="submit"
          className="action-pill action-pill--md"
          disabled={isSaveDisabled}
        >
          {mutation.isPending
            ? copy.saving
            : savedFeedback
              ? copy.saved
              : copy.save}
        </button>
      </div>
    </form>
  );
}