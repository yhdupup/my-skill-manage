import { ErrorBanner } from "../../../components/ErrorBanner";
import { LoadingSpinner } from "../../../components/LoadingSpinner";
import { PageHeader } from "../../../components/PageHeader";
import { ReferenceContextWindowSection } from "../components/ReferenceContextWindowSection";
import { SettingsHarnessCard } from "../components/SettingsHarnessCard";
import { useSettingsCopy } from "../i18n";
import { useSettingsPageController } from "../model/use-settings-page-controller";

export default function SettingsPage() {
  const copy = useSettingsCopy();
  const controller = useSettingsPageController({
    unableToUpdateHarnessSupport: copy.errors.unableToUpdateHarnessSupport,
    unableToUpdateContextWindow: copy.errors.unableToUpdateContextWindow,
  });

  return (
    <>
      <div className="page-chrome">
        <PageHeader
          title={copy.title}
          subtitle={copy.subtitle}
        />
      </div>

      {controller.errorMessage ? (
        <ErrorBanner message={controller.errorMessage} onDismiss={() => controller.setErrorMessage("")} />
      ) : null}

      {controller.isPending ? (
        <div className="panel-state">
          <LoadingSpinner label={copy.loading} />
        </div>
      ) : !controller.data ? (
        <div className="panel-state">
          <p className="muted-text">{copy.errors.unableToLoad}</p>
        </div>
      ) : (
        <>
          <section className="settings-section">
            <h2 className="settings-section__heading">{copy.referenceContextWindow.heading}</h2>
            <ReferenceContextWindowSection
              copy={copy.referenceContextWindow}
              unableToUpdateMessage={copy.errors.unableToUpdateContextWindow}
            />
          </section>

          <section className="settings-section">
            <h2 className="settings-section__heading">{copy.harnesses.heading}</h2>
            {controller.data.harnesses.map((harness) => (
              <SettingsHarnessCard
                key={harness.harness}
                harness={harness}
                pending={controller.isHarnessPending(harness.harness)}
                copy={copy.harnesses}
                onToggle={controller.handleSupportToggle}
              />
            ))}
          </section>
        </>
      )}
    </>
  );
}
