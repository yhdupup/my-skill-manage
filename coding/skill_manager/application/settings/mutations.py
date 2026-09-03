from __future__ import annotations

from skill_manager.errors import MutationError
from skill_manager.harness import HarnessKernelService
from skill_manager.harness.support_store import HarnessSupportStore

from ..invalidation import InvalidationFanout


class SettingsMutationService:
    def __init__(
        self,
        harness_kernel: HarnessKernelService,
        support_store: HarnessSupportStore,
        invalidation: InvalidationFanout,
    ) -> None:
        self.harness_kernel = harness_kernel
        self.support_store = support_store
        self.invalidation = invalidation

    def set_harness_support(self, harness: str, enabled: bool) -> dict[str, object]:
        if not self.harness_kernel.is_known_harness(harness):
            raise MutationError(f"unknown harness: {harness}", status=404)
        document = self.support_store.set_enabled(harness, enabled)
        self.invalidation.invalidate_all()
        return {
            "ok": True,
            "enabled": enabled,
            "contextWindowTokens": document.context_window_tokens,
        }

    def set_context_window_tokens(self, value: int) -> dict[str, object]:
        document = self.support_store.set_context_window_tokens(value)
        self.invalidation.invalidate_all()
        return {"ok": True, "contextWindowTokens": document.context_window_tokens}