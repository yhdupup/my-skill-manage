from __future__ import annotations

from skill_manager.harness import HarnessKernelService
from skill_manager.harness.support_store import HarnessSupportStore
from skill_manager.paths import AppPaths

from .presenters import settings_payload


class SettingsQueryService:
    def __init__(
        self,
        harness_kernel: HarnessKernelService,
        paths: AppPaths,
        support_store: HarnessSupportStore,
    ) -> None:
        self.harness_kernel = harness_kernel
        self.paths = paths
        self.support_store = support_store

    def get_settings(self) -> dict[str, object]:
        return settings_payload(
            paths=self.paths,
            platform=self.harness_kernel.context.platform,
            harness_statuses=self.harness_kernel.harness_statuses(),
            enabled_harnesses=self.harness_kernel.enabled_harness_ids(),
            settings_document=self.support_store.load_document(),
        )

    def get_context_window_tokens(self) -> int:
        return self.support_store.context_window_tokens()