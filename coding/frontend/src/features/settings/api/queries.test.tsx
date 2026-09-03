import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mcpManagementKeys } from "../../mcp/public";
import { skillsKeys } from "../../skills/public";
import { okJson } from "../../../test/fetch";
import { renderWithAppProviders } from "../../../test/render";
import {
  settingsKeys,
  useContextWindowMutation,
  useContextWindowQuery,
  useHarnessSupportMutation,
} from "./queries";

const fetchMock = vi.fn();

function HarnessSupportProbe() {
  const mutation = useHarnessSupportMutation();

  return (
    <button
      type="button"
      onClick={() => mutation.mutate({ harness: "codex", enabled: false })}
    >
      Disable Codex support
    </button>
  );
}

function ContextWindowProbe({ value }: { value: number }) {
  const mutation = useContextWindowMutation();
  const query = useContextWindowQuery();

  return (
    <div>
      <span data-testid="current-window">{query.data ?? "missing"}</span>
      <span data-testid="loading">{query.isLoading ? "yes" : "no"}</span>
      <button
        type="button"
        onClick={() => {
          mutation.mutate(value);
        }}
      >
        Save window
      </button>
    </div>
  );
}

describe("settings queries", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it("invalidates settings, skills, and MCP after harness support changes", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url === "/api/settings/harnesses/codex/support") {
        expect(init?.method).toBe("PUT");
        expect(JSON.parse(String(init?.body))).toEqual({ enabled: false });
        return okJson({ ok: true, enabled: false });
      }
      throw new Error(`Unhandled URL ${url}`);
    });

    const { queryClient } = renderWithAppProviders(<HarnessSupportProbe />);
    queryClient.setQueryData(settingsKeys.detail(), {
      storage: {
        platform: "linux",
        configDir: "/tmp/config/skill-manager",
        dataDir: "/tmp/data/skill-manager",
        stateDir: "/tmp/state/skill-manager",
        skillsStorePath: "/tmp/data/skill-manager/shared",
        marketplaceCachePath: "/tmp/data/skill-manager/marketplace",
        settingsPath: "/tmp/config/skill-manager/settings.json",
      },
      harnesses: [
        {
          harness: "codex",
          label: "Codex",
          logoKey: "codex",
          supportEnabled: true,
          installed: true,
          managedLocation: "/tmp/codex",
        },
      ],
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    fireEvent.click(screen.getByRole("button", { name: "Disable Codex support" }));

    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: mcpManagementKeys.all }),
    );
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: settingsKeys.all });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: skillsKeys.list() });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: skillsKeys.detailPrefix() });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: skillsKeys.sourceStatusPrefix() });
  });

  it("exposes the current context window through useContextWindowQuery", async () => {
    fetchMock.mockImplementation(async () =>
      okJson({
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
      }),
    );

    renderWithAppProviders(<ContextWindowProbe value={64000} />);
    await waitFor(() =>
      expect(screen.getByTestId("current-window").textContent).toBe("128000"),
    );
  });

  it("optimistically applies a new context window and rolls back on failure", async () => {
    let shouldFail = true;
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url === "/api/settings/context-window") {
        expect(init?.method).toBe("PUT");
        expect(JSON.parse(String(init?.body))).toEqual({ contextWindowTokens: 64000 });
        // Defer so onMutate is observable before onError fires.
        await new Promise((resolve) => setTimeout(resolve, 5));
        if (shouldFail) {
          return new Response(JSON.stringify({ error: "boom" }), {
            status: 500,
            headers: { "Content-Type": "application/json" },
          });
        }
        return okJson({ ok: true, contextWindowTokens: 64000 });
      }
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

    const { queryClient } = renderWithAppProviders(<ContextWindowProbe value={64000} />);
    await waitFor(() =>
      expect(screen.getByTestId("current-window").textContent).toBe("128000"),
    );

    fireEvent.click(screen.getByRole("button", { name: "Save window" }));

    // Optimistic update applied immediately.
    await waitFor(() =>
      expect(screen.getByTestId("current-window").textContent).toBe("64000"),
    );

    // Failure path rolls back to the original 128000.
    await waitFor(() =>
      expect(screen.getByTestId("current-window").textContent).toBe("128000"),
    );

    // Happy path: now succeed and verify invalidations fire.
    shouldFail = false;
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    fireEvent.click(screen.getByRole("button", { name: "Save window" }));

    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: mcpManagementKeys.all }),
    );
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: settingsKeys.all });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: skillsKeys.list() });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: skillsKeys.detailPrefix() });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: skillsKeys.sourceStatusPrefix() });
  });
});
