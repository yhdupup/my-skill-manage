import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { LocaleProvider, useCommonCopy, useLocale } from ".";

function LocaleProbe() {
  const { locale } = useLocale();
  const common = useCommonCopy();

  return (
    <div>
      <p data-testid="locale">{locale}</p>
      <p>{common.nav.overview}</p>
      <p>{common.nav.skills}</p>
      <p>{common.nav.mcpServers}</p>
      <p>{common.nav.clis}</p>
    </div>
  );
}

describe("LocaleProvider (Chinese-only build)", () => {
  afterEach(() => {
    document.documentElement.lang = "zh-CN";
  });

  it("defaults to Chinese", () => {
    render(
      <LocaleProvider>
        <LocaleProbe />
      </LocaleProvider>,
    );

    expect(screen.getByTestId("locale")).toHaveTextContent("zh-CN");
    expect(screen.getByText("总览")).toBeInTheDocument();
  });

  it("always reports the active locale as zh-CN", () => {
    window.localStorage.setItem("skill-manager:locale", "en");
    render(
      <LocaleProvider>
        <LocaleProbe />
      </LocaleProvider>,
    );
    expect(screen.getByTestId("locale")).toHaveTextContent("zh-CN");
  });

  it("renders the protected product names", () => {
    window.localStorage.setItem("skill-manager:locale", "zh-CN");
    render(
      <LocaleProvider>
        <LocaleProbe />
      </LocaleProvider>,
    );
    expect(screen.getByText("技能")).toBeInTheDocument();
    expect(screen.getByText("MCP 服务器")).toBeInTheDocument();
    expect(screen.getByText("命令行工具")).toBeInTheDocument();
  });
});