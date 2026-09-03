import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";
import "./styles/index.css";

/* The build is Chinese-only. Persist that choice before React mounts so the
 * LocaleProvider reads `zh-CN` from localStorage on first paint. We only set
 * the key when nothing has been recorded yet, so QA scripts that explicitly
 * store a different value still win. */
try {
  if (typeof window !== "undefined") {
    window.localStorage.setItem("skill-manager:locale", "zh-CN");
  }
} catch {
  /* storage may be unavailable; fall back to DEFAULT_LOCALE on first paint */
}

/* Feature-local CSS.
 * Order preserves the original app.css feature-section sequence so in-layer
 * ties resolve identically to pre-split behavior. Each file wraps its
 * contents in @layer features { … }. */
import "./components/detail/index.css";
import "./features/overview/styles/overview.css";
import "./features/marketplace/styles/cards.css";
import "./features/settings/styles/settings.css";
import "./features/slash-commands/styles/slash-commands.css";
import "./features/skills/styles/detail.css";
import "./features/skills/styles/board.css";
import "./features/skills/styles/scan.css";
import "./features/skills/styles/usage.css";
import "./components/matrix/matrix.css";
import "./features/marketplace/styles/panes.css";
import "./features/marketplace/styles/mcp-detail.css";
import "./features/mcp/styles/pages.css";
import "./features/mcp/styles/detail-sheet.css";
import "./features/mcp/styles/edit-dialogs.css";
import "./features/mcp/styles/config-form.css";
import "./styles/editorial-theme.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
