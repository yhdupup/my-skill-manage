import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useSkillDetailController } from "../../model/use-skill-detail-controller";
import { SkillDetailView } from "./SkillDetailView";

vi.mock("../../model/use-skill-detail-controller", () => ({
  useSkillDetailController: vi.fn(),
}));

const useSkillDetailControllerMock = vi.mocked(useSkillDetailController);

function renderSubject() {
  return render(
    <SkillDetailView
      skillRef="shared:trace-lens"
      pendingToggleHarnesses={new Set()}
      pendingStructuralAction={null}
      onClose={vi.fn()}
      onManageSkill={vi.fn(async () => undefined)}
      onToggleSkill={vi.fn(async () => undefined)}
      onUpdateSkill={vi.fn(async () => undefined)}
      onRemoveSkill={vi.fn(async () => undefined)}
      onDeleteSkill={vi.fn(async () => undefined)}
    />,
  );
}

describe("SkillDetailView", () => {
  it("shows a loading shell without skill actions while the detail query is pending", () => {
    useSkillDetailControllerMock.mockReturnValue({
      detail: null,
      isInitialLoading: true,
      queryErrorMessage: "",
      actionErrorMessage: "",
      isRemoveDialogOpen: false,
      isDeleteDialogOpen: false,
      dismissActionError: vi.fn(),
      onManage: vi.fn(),
      onToggleHarness: vi.fn(),
      onUpdate: vi.fn(),
      requestRemove: vi.fn(),
      requestDelete: vi.fn(),
      setRemoveDialogOpen: vi.fn(),
      setDeleteDialogOpen: vi.fn(),
      handleConfirmDelete: vi.fn(),
      handleConfirmRemove: vi.fn(),
    });

    renderSubject();

    expect(screen.getByText("正在加载")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "关闭技能详情" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Skill actions")).not.toBeInTheDocument();
  });

  it("shows an error fallback without a skill action rail when loading fails", () => {
    useSkillDetailControllerMock.mockReturnValue({
      detail: null,
      isInitialLoading: false,
      queryErrorMessage: "boom",
      actionErrorMessage: "",
      isRemoveDialogOpen: false,
      isDeleteDialogOpen: false,
      dismissActionError: vi.fn(),
      onManage: vi.fn(),
      onToggleHarness: vi.fn(),
      onUpdate: vi.fn(),
      requestRemove: vi.fn(),
      requestDelete: vi.fn(),
      setRemoveDialogOpen: vi.fn(),
      setDeleteDialogOpen: vi.fn(),
      handleConfirmDelete: vi.fn(),
      handleConfirmRemove: vi.fn(),
    });

    renderSubject();

    expect(screen.getByText("无法加载技能")).toBeInTheDocument();
    expect(screen.getByText("请重新选择此技能，或回到列表后再次打开。")).toBeInTheDocument();
    expect(screen.queryByLabelText("Skill actions")).not.toBeInTheDocument();
  });
});
