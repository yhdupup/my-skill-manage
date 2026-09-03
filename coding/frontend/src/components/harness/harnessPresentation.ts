import claudeLogo from "../../assets/harness-logos/claude-code-logo.svg";
import codexLogo from "../../assets/harness-logos/codex-logo.svg";
import cursorLogo from "../../assets/harness-logos/cursor-logo.svg";
import hermesLogo from "../../assets/harness-logos/hermes-logo.png";
import openclawLogo from "../../assets/harness-logos/openclaw-logo.svg";
import opencodeLogo from "../../assets/harness-logos/opencode-logo.svg";

export type HarnessLogoKey = "claude" | "codex" | "cursor" | "hermes" | "opencode" | "openclaw";

interface HarnessPresentation {
  logoSrc: string;
  variant: HarnessLogoKey;
}

const HARNESS_LOGO_ASSETS: Record<HarnessLogoKey, HarnessPresentation> = {
  claude: {
    logoSrc: claudeLogo,
    variant: "claude",
  },
  codex: {
    logoSrc: codexLogo,
    variant: "codex",
  },
  cursor: {
    logoSrc: cursorLogo,
    variant: "cursor",
  },
  hermes: {
    logoSrc: hermesLogo,
    variant: "hermes",
  },
  opencode: {
    logoSrc: opencodeLogo,
    variant: "opencode",
  },
  openclaw: {
    logoSrc: openclawLogo,
    variant: "openclaw",
  },
};

export function getHarnessPresentation(logoKey: string | null | undefined): HarnessPresentation | null {
  if (!logoKey) {
    return null;
  }
  return HARNESS_LOGO_ASSETS[logoKey as HarnessLogoKey] ?? null;
}
