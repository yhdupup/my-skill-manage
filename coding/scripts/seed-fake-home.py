"""Seed a temporary fake home with the mixed fixture so the running backend
sees a representative mix of managed / unmanaged / Trae skills."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, "/Users/a1234/Desktop/个人项目/skill管理/coding")

os.environ.update({
    "HOME": "/tmp/sm-stage4-smoke/home",
    "XDG_CONFIG_HOME": "/tmp/sm-stage4-smoke/config",
    "XDG_DATA_HOME": "/tmp/sm-stage4-smoke/data",
    "XDG_STATE_HOME": "/tmp/sm-stage4-smoke/state",
})

from tests.support.fake_home import create_fake_home_spec, seed_mixed_fixture, seed_skill_package

spec = create_fake_home_spec(Path("/tmp/sm-stage4-smoke"))
seed_mixed_fixture(spec)

# Add a Chinese-heavy skill to exercise the wide-character estimator.
seed_skill_package(
    spec.skills_store_root,
    "zh-heavy",
    "中文压测 Skill",
    body="汉字测试" * 200,
    description="中文密集的 Skill 用于演示上下文估算",
    source_kind="github",
    source_locator="github:example-org/zh-heavy",
)
seed_skill_package(
    spec.codex_root,
    "codex-extra",
    "Codex Extra",
    body="extra ascii text",
)

# Add a tiny english skill for variety.
seed_skill_package(
    spec.codex_root,
    "english-small",
    "English Small",
    body="a" * 200,
)
print("seeded mixed fixture + extras under", spec.root)