import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { okJson } from "../../../test/fetch";
import { renderWithAppProviders } from "../../../test/render";
import SettingsPage from "./SettingsPage";

const fetchMock = vi.fn();

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it("does not render backend-provided local storage paths", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url === "/api/settings") {
        return okJson({
          contextWindowTokens: 128000,
          storage: {
            platform: "linux",
            configDir: "/tmp/config/skill-manager",
            dataDir: "/tmp/data/skill-manager",
            stateDir: "/tmp/state/skill-manager",
            skillsStorePath: "/tmp/data/skill-manager/shared",
            marketplaceCachePath: "/tmp/data/skill-manager/marketplace",
            settingsPath: "/tmp/config/skill-manager/settings.json",
          },
          harnesses: [],
        });
      }
      throw new Error(`Unhandled URL ${url}`);
    });

    renderWithAppProviders(<SettingsPage />);

    expect(await screen.findByLabelText(/参考窗口/)).toBeInTheDocument();
    expect(screen.queryByText("/tmp/data/skill-manager/shared")).not.toBeInTheDocument();
    expect(screen.queryByText("/tmp/data/skill-manager/marketplace")).not.toBeInTheDocument();
    expect(screen.queryByText("本地存储")).not.toBeInTheDocument();
  });
});
