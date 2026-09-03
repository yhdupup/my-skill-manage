import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { LOCALE_STORAGE_KEY } from "./i18n";
import { createRouteFetchMock, okJson } from "./test/fetch";
import { mcpInventoryEntry, mcpInventoryPayload } from "./test/fixtures/mcp";
import { skillsPayload } from "./test/fixtures/skills";
import { renderWithRouter, stubDesktopMatchMedia } from "./test/render";

const fetchMock = vi.fn();

function renderApp(initialRoute = "/") {
  return renderWithRouter(<App />, { route: initialRoute });
}

function stubEmptyApi() {
  fetchMock.mockImplementation(
    createRouteFetchMock(
      [
        { match: "/api/skills", response: skillsPayload() },
        { match: "/api/scan/configs", response: { configs: [], activeId: null } },
        { match: "/api/mcp/servers", response: mcpInventoryPayload() },
        { match: "/api/settings", response: settingsPayload() },
        { match: "/api/slash-commands", response: slashCommandsPayload() },
        {
          match: (url) =>
            url.startsWith("/api/marketplace/popular") ||
            url.startsWith("/api/marketplace/search") ||
            url.startsWith("/api/marketplace/clis/popular") ||
            url.startsWith("/api/marketplace/clis/search"),
          response: { items: [], nextOffset: null, hasMore: false },
        },
      ],
      () => okJson({}),
    ),
  );
}

describe("App shell", () => {
  beforeEach(() => {
    // Pin to the Chinese-only build; do not clear so the locale set by
    // global setup survives across tests.
    window.localStorage.setItem("skill-manager:locale", "zh-CN");
    document.documentElement.lang = "zh-CN";
    stubDesktopMatchMedia();
    stubEmptyApi();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    document.documentElement.lang = "zh-CN";
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("renders the utility settings entry without a top tab bar", async () => {
    renderApp("/overview");
    await waitFor(() => expect(screen.getByRole("heading", { name: /Skills\. 自动管理/ })).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /设置/ })).toBeInTheDocument();
    expect(document.querySelector(".app-header")).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: /主导航/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /^技能/ })).not.toBeInTheDocument();
    expect(document.querySelector(".sidebar")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Scan Config/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Slash Commands/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /MCP Servers/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Marketplace/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Refresh/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Light/i })).not.toBeInTheDocument();
  });

  it("keeps the return-home entry available before settings data resolves", () => {
    fetchMock.mockImplementation(
      () => new Promise<Response>(() => {
        // Keep the query pending so the navigation renders its unloaded state.
      }),
    );

    renderApp("/settings");

    expect(screen.getByRole("link", { name: /返回首页/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /斜杠命令/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /MCP 服务器/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /应用商店/i })).not.toBeInTheDocument();
  });

  it("does not show skill section navigation", async () => {
    renderApp("/settings");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /设置/ })).toBeInTheDocument(),
    );
    expect(screen.queryByRole("navigation", { name: /^技能$/ })).not.toBeInTheDocument();
  });

  it.each([
    ["/overview", "Skills. 自动管理。"],
    ["/settings", "设置"],
  ])("renders the expected page heading for %s", async (route, heading) => {
    renderApp(route);
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument(),
    );
  });

  it("redirects deleted routes (scan-config, mcp, slash-commands, marketplace) to /overview", async () => {
    for (const route of [
      "/scan-config",
      "/mcp/use",
      "/mcp/review",
      "/slash-commands",
      "/slash-commands/use",
      "/slash-commands/review",
      "/marketplace",
      "/marketplace/skills",
      "/marketplace/mcp",
      "/marketplace/clis",
    ]) {
      const utils = renderApp(route);
      await waitFor(() =>
        expect(screen.getByRole("heading", { name: /Skills\. 自动管理/ })).toBeInTheDocument(),
      );
      utils.unmount();
    }
  });

  it("redirects / to /overview", async () => {
    renderApp("/");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /Skills\. 自动管理/ })).toBeInTheDocument(),
    );
  });

  it("shows managed skills on overview, toggles harness state, and opens existing details", async () => {
    fetchMock.mockImplementation(
      createRouteFetchMock(
        [
          { match: "/api/skills", response: overviewSkillsPayload() },
          { match: "/api/settings", response: settingsPayload() },
        ],
        () => okJson({ ok: true }),
      ),
    );

    renderApp("/overview");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Writer" })).toBeInTheDocument(),
    );
    expect(screen.queryByText(/Token/)).not.toBeInTheDocument();
    expect(screen.getByText("2.50%")).toBeInTheDocument();
    expect(screen.queryByText("Review me")).not.toBeInTheDocument();
    expect(screen.queryByText("Cursor")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("switch", { name: /关闭 Writer 在 Codex/ }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/skills/writer/disable",
        expect.objectContaining({ method: "POST" }),
      ),
    );

    fireEvent.click(screen.getByRole("link", { name: /查看 Writer 详情/ }));
    await waitFor(() =>
      expect(screen.getByRole("dialog")).toBeInTheDocument(),
    );
  });

  it("filters the overview list instantly by search and enabled state", async () => {
    fetchMock.mockImplementation(
      createRouteFetchMock(
        [
          { match: "/api/skills", response: overviewSkillsPayload() },
          { match: "/api/settings", response: settingsPayload() },
        ],
        () => okJson({ ok: true }),
      ),
    );

    renderApp("/overview");
    expect(await screen.findByRole("heading", { name: "Writer" })).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: /按名称或简介搜索 Skill/ }), {
      target: { value: "missing" },
    });
    expect(screen.getByText(/没有符合当前搜索和筛选条件/)).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: /按名称或简介搜索 Skill/ }), {
      target: { value: "writer" },
    });
    expect(screen.getByRole("heading", { name: "Writer" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "未开启" }));
    expect(screen.getByText(/没有符合当前搜索和筛选条件/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "已开启" }));
    expect(screen.getByRole("heading", { name: "Writer" })).toBeInTheDocument();
  });

  it("redirects retired /harnesses to /overview", async () => {
    renderApp("/harnesses");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /Skills\. 自动管理/ })).toBeInTheDocument(),
    );
  });

  it("navigates to overview from the contextual return entry", async () => {
    renderApp("/settings");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /设置/ })).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("link", { name: /返回首页/ }));

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /Skills\. 自动管理/ })).toBeInTheDocument(),
    );
  });

  it("does not render a language switcher", async () => {
    renderApp("/settings");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /设置/ })).toBeInTheDocument(),
    );
    // An earlier build offered a navigation control that toggled
    // between English and Chinese. The footer now hides that switcher
    // because the Chinese-only build does not need runtime language
    // switching.
    expect(screen.queryByRole("button", { name: /Language: English/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/语言切换|Interface language/)).not.toBeInTheDocument();
  });
});

function overviewSkillsPayload() {
  const contextUsage = {
    estimatedTokens: 3200,
    contextWindowTokens: 128000,
    usagePercent: 2.5,
    status: "normal" as const,
    reason: null,
  };
  return skillsPayload({
    managed: 1,
    unmanaged: 1,
    harnessColumns: [
      { harness: "codex", label: "Codex", installed: true, logoKey: "codex" },
      { harness: "trae", label: "Trae CN", installed: true, logoKey: "trae" },
      { harness: "cursor", label: "Cursor", installed: false, logoKey: "cursor" },
    ],
    rows: [
      {
        skillRef: "writer",
        name: "Writer",
        description: "Writes concise product copy.",
        displayStatus: "Managed",
        actions: { canManage: false, canStopManaging: true, canDelete: true },
        contextUsage,
        cells: [
          { harness: "codex", label: "Codex", logoKey: "codex", state: "enabled", interactive: true },
          { harness: "trae", label: "Trae CN", logoKey: "trae", state: "disabled", interactive: true },
          { harness: "cursor", label: "Cursor", logoKey: "cursor", state: "empty", interactive: false },
        ],
      },
      {
        skillRef: "review-me",
        name: "Review me",
        description: "Not managed.",
        displayStatus: "Unmanaged",
        actions: { canManage: true, canStopManaging: false, canDelete: false },
        contextUsage,
        cells: [],
      },
    ],
  });
}

function slashCommandsPayload({ count = 0, reviewCount = 0 }: { count?: number; reviewCount?: number } = {}) {
  return {
    storePath: "/tmp/home/Library/Application Support/skill-manager/slash-commands/commands",
    syncStatePath: "/tmp/home/Library/Application Support/skill-manager/slash-commands/sync-state.json",
    targets: [
      {
        id: "opencode",
        label: "OpenCode",
        rootPath: "/tmp/home/.config/opencode",
        outputDir: "/tmp/home/.config/opencode/commands",
        invocationPrefix: "/",
        renderFormat: "frontmatter_markdown",
        scope: "global",
        docsUrl: "https://opencode.ai/docs/commands/",
        fileGlob: "*.md",
        supportsFrontmatter: true,
        supportNote: null,
        enabled: true,
        available: true,
        defaultSelected: true,
      },
      {
        id: "claude",
        label: "Claude Code",
        rootPath: "/tmp/home/.claude",
        outputDir: "/tmp/home/.claude/commands",
        invocationPrefix: "/",
        renderFormat: "frontmatter_markdown",
        scope: "global",
        docsUrl: "https://code.claude.com/docs/en/slash-commands",
        fileGlob: "*.md",
        supportsFrontmatter: true,
        supportNote: null,
        enabled: true,
        available: true,
        defaultSelected: true,
      },
      {
        id: "cursor",
        label: "Cursor",
        rootPath: "/tmp/home/.cursor",
        outputDir: "/tmp/home/.cursor/commands",
        invocationPrefix: "/",
        renderFormat: "cursor_plaintext",
        scope: "global",
        docsUrl: "https://cursor.com/changelog/1-6",
        fileGlob: "*.md",
        supportsFrontmatter: false,
        supportNote: null,
        enabled: true,
        available: true,
        defaultSelected: true,
      },
      {
        id: "codex",
        label: "Codex",
        rootPath: "/tmp/home/.codex",
        outputDir: "/tmp/home/.codex/prompts",
        invocationPrefix: "/prompts:",
        renderFormat: "frontmatter_markdown",
        scope: "global",
        docsUrl: "https://developers.openai.com/codex/custom-prompts",
        fileGlob: "*.md",
        supportsFrontmatter: true,
        supportNote: null,
        enabled: true,
        available: true,
        defaultSelected: true,
      },
    ],
    defaultTargets: ["opencode", "claude", "cursor", "codex"],
    commands: Array.from({ length: count }, (_item, index) => ({
      name: `command-${index + 1}`,
      description: `Command ${index + 1}`,
      prompt: "$ARGUMENTS",
      syncTargets: [],
    })),
    reviewCommands: Array.from({ length: reviewCount }, (_item, index) => ({
      reviewRef: `codex:review-${index + 1}`,
      kind: "unmanaged",
      target: "codex",
      targetLabel: "Codex",
      name: `review-${index + 1}`,
      path: `/tmp/home/.codex/prompts/review-${index + 1}.md`,
      description: `Review command ${index + 1}`,
      prompt: "$ARGUMENTS",
      commandExists: false,
      canImport: true,
      actions: ["import"],
      error: null,
    })),
  };
}

function settingsPayload() {
  return {
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
  };
}
