import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import RouteLoadingPanel from "./components/RouteLoadingPanel";
import { Shell } from "./components/Shell";
import { ToastProvider } from "./components/Toast";
import { UiTooltipProvider } from "./components/ui/UiTooltipProvider";
import { SkillsWorkspaceSessionProvider } from "./features/skills/public";
import { LocaleProvider, useCommonCopy } from "./i18n";

const OverviewPage = lazy(() => import("./features/overview/screens/OverviewPage"));
const SettingsPage = lazy(() => import("./features/settings/screens/SettingsPage"));

export function App() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <LocaleProvider>
        <ToastProvider>
          <UiTooltipProvider>
            <AppContent />
          </UiTooltipProvider>
        </ToastProvider>
      </LocaleProvider>
    </QueryClientProvider>
  );
}

function AppContent() {
  const common = useCommonCopy();

  return (
    <SkillsWorkspaceSessionProvider>
      <Shell>
        <Routes>
          <Route index element={<Navigate to="/overview" replace />} />

          <Route
            path="overview"
            element={
              <Suspense fallback={<RouteLoadingPanel label={common.loading.overview} />}>
                <OverviewPage />
              </Suspense>
            }
          />

          <Route
            path="settings"
            element={
              <Suspense fallback={<RouteLoadingPanel label={common.loading.settings} />}>
                <SettingsPage />
              </Suspense>
            }
          />

          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </Shell>
    </SkillsWorkspaceSessionProvider>
  );
}
