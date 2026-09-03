import { ArrowLeft, Settings } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

export function AppUtilityNav() {
  const location = useLocation();
  const onSettingsPage = location.pathname.startsWith("/settings");
  const label = onSettingsPage ? "返回首页" : "设置";
  const Icon = onSettingsPage ? ArrowLeft : Settings;

  return (
    <Link className="app-utility-nav" to={onSettingsPage ? "/overview" : "/settings"} aria-label={label} title={label}>
      <Icon size={18} aria-hidden="true" />
      <span className="u-visually-hidden">{label}</span>
    </Link>
  );
}
