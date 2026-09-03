import type { ReactNode } from "react";

import { AppUtilityNav } from "./AppUtilityNav";
import { DotPattern } from "./ui/DotPattern";

interface ShellProps {
  children: ReactNode;
}

export function Shell({ children }: ShellProps) {
  return (
    <div className="app-shell">
      <DotPattern className="app-background-pattern" width={16} height={16} cr={0.9} />
      <AppUtilityNav />
      <main className="app-main ui-scrollbar">
        <div className="page-shell">{children}</div>
      </main>
    </div>
  );
}
