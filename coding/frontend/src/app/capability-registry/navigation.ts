import { useCommonCopy } from "../../i18n";

export interface NavigationLinkModel {
  key: string;
  to: string;
  label: string;
  count?: number | null;
}

export interface NavigationModel {
  settingsLink: NavigationLinkModel;
}

export function useNavigationModel(): NavigationModel {
  const common = useCommonCopy();
  return {
    settingsLink: {
      key: "settings",
      to: "/settings",
      label: common.nav.settings,
    },
  };
}
