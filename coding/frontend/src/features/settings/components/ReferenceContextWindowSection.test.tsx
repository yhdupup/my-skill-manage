import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { okJson } from "../../../test/fetch";
import { renderWithAppProviders } from "../../../test/render";
import { ReferenceContextWindowSection } from "./ReferenceContextWindowSection";

const fetchMock = vi.fn();

const enCopy = {
  heading: "Reference context window",
  description: "Adjust to match your model.",
  tooltip: "Estimate only.",
  label: "Reference window in tokens",
  placeholder: "e.g. 128000",
  save: "Save",
  saving: "Saving...",
  saved: "Saved",
  invalidPositiveInteger: "Enter a positive whole number.",
  tooSmall: "Use at least 1 token.",
} as const;

describe("ReferenceContextWindowSection", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it("renders the current value with default 128000 and disables save until edited", async () => {
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

    renderWithAppProviders(
      <ReferenceContextWindowSection copy={enCopy} unableToUpdateMessage="Unable to save the context window." />,
    );

    const input = (await screen.findByLabelText(enCopy.label)) as HTMLInputElement;
    await waitFor(() => expect(input.value).toBe("128000"));
    const save = screen.getByRole("button", { name: enCopy.save });
    expect(save).toBeDisabled();
  });

  it("rejects invalid input and keeps the save button disabled", async () => {
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

    renderWithAppProviders(
      <ReferenceContextWindowSection copy={enCopy} unableToUpdateMessage="Unable to save the context window." />,
    );

    const input = (await screen.findByLabelText(enCopy.label)) as HTMLInputElement;

    fireEvent.change(input, { target: { value: "0" } });
    expect(input.value).toBe("0");
    expect(screen.getByText(enCopy.invalidPositiveInteger)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: enCopy.save })).toBeDisabled();

    fireEvent.change(input, { target: { value: "abc" } });
    expect(input.value).toBe("");

    fireEvent.change(input, { target: { value: "1.5" } });
    expect(input.value).toBe("15");
  });

  it("saves the new value, swaps the button label to Saved, and resets", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
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
      if (url === "/api/settings/context-window") {
        expect(init?.method).toBe("PUT");
        expect(JSON.parse(String(init?.body))).toEqual({ contextWindowTokens: 64000 });
        return okJson({ ok: true, contextWindowTokens: 64000 });
      }
      throw new Error(`Unhandled URL ${url}`);
    });

    renderWithAppProviders(
      <ReferenceContextWindowSection copy={enCopy} unableToUpdateMessage="Unable to save the context window." />,
    );

    const input = (await screen.findByLabelText(enCopy.label)) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "64000" } });
    const save = screen.getByRole("button", { name: enCopy.save });
    expect(save).not.toBeDisabled();
    fireEvent.click(save);

    await waitFor(() => expect(screen.getByRole("button", { name: enCopy.saved })).toBeInTheDocument());
  });

  it("keeps the draft on a failed save and surfaces the error", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
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
      if (url === "/api/settings/context-window") {
        return new Response(JSON.stringify({ error: "boom" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        });
      }
      throw new Error(`Unhandled URL ${url}`);
    });

    renderWithAppProviders(
      <ReferenceContextWindowSection copy={enCopy} unableToUpdateMessage="Unable to save the context window." />,
    );

    const input = (await screen.findByLabelText(enCopy.label)) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "64000" } });
    fireEvent.click(screen.getByRole("button", { name: enCopy.save }));

    await waitFor(() => expect(input.value).toBe("64000"));
  });
});