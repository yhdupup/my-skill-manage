import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

import { installMockLocalStorage } from "./local-storage";

try {
  if (typeof window.localStorage.clear !== "function") {
    installMockLocalStorage();
  }
} catch {
  installMockLocalStorage();
}

// Pin the locale to the Chinese-only build so every test renders the same
// copy that the production app serves.
try {
  window.localStorage.setItem("skill-manager:locale", "zh-CN");
  document.documentElement.lang = "zh-CN";
} catch {
  /* storage may be unavailable in some test environments */
}

if (typeof ResizeObserver === "undefined") {
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

  vi.stubGlobal("ResizeObserver", ResizeObserver);
}
