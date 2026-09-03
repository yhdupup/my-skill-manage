import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConfirmActionDialog } from "./ConfirmActionDialog";

function renderDialog(props: Partial<Parameters<typeof ConfirmActionDialog>[0]> = {}) {
  const onOpenChange = vi.fn();
  const onConfirm = vi.fn();

  const utils = render(
    <ConfirmActionDialog
      open
      title="卸载 Exa Search?（中文）"
      description="从中央目录移除此服务器。"
      note="此操作会更新本地 harness 配置文件。"
      confirmLabel="卸载"
      pendingLabel="卸载中"
      isPending={false}
      onOpenChange={onOpenChange}
      onConfirm={onConfirm}
      {...props}
    />,
  );

  return { ...utils, onOpenChange, onConfirm };
}

describe("ConfirmActionDialog", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "ResizeObserver",
      class ResizeObserver {
        observe() {}
        unobserve() {}
        disconnect() {}
      },
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the title, description, and secondary note in the standard dialog body", () => {
    renderDialog();
    expect(screen.getByRole("heading", { name: /卸载 exa search\?（中文）/i })).toBeInTheDocument();
    expect(screen.getByText(/从中央目录移除此服务器/i)).toBeInTheDocument();
    expect(screen.getByText(/此操作会更新本地 harness 配置文件/i)).toBeInTheDocument();
  });

  it("closes through the cancel button when not pending", () => {
    const { onOpenChange } = renderDialog();
    fireEvent.click(screen.getByRole("button", { name: /取消/ }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("disables the footer while pending", () => {
    renderDialog({ isPending: true });
    expect(screen.getByRole("button", { name: /取消/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /(卸载中|Deleting)/ })).toBeDisabled();
  });
});
