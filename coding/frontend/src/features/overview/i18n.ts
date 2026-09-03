import { useLocalizedCopy, type CopyShape, type LocalizedCopy } from "../../i18n";

const englishOverviewCopy = {
  screen: {
    title: "Skills. Under control.",
    titlePrimary: "Skills.",
    titleSecondary: "Under control.",
    eyebrow: "Local AI workspace",
    subtitle: "One calm place to review context usage and control every installed AI coding tool.",
    unableToLoadSkills: (message: string) => `Unable to load skills: ${message}`,
  },
  sections: {
    inventoryStatistics: "Skill usage summary",
    skillsInUse: "Skills in use",
    skillsInUseDescription: "Manage where each skill is enabled and review its estimated context cost.",
    noSkillsInUse: "No skills are currently managed by Skill Manager.",
    noMatchingSkills: "No skills match the current search and filter.",
    searchPlaceholder: "Search skills",
    searchLabel: "Search skills by name or description",
    filterAll: "All",
    filterEnabled: "Enabled",
    filterDisabled: "Disabled",
  },
  stats: {
    inUse: "In use",
    enabledBindings: "Enabled bindings",
    inUseDetail: "managed by Skill Manager",
    enabledBindingsDetail: "across installed harnesses",
  },
} as const;

export type OverviewCopy = CopyShape<typeof englishOverviewCopy>;

export const overviewCopy = {
  en: englishOverviewCopy,
  "zh-CN": {
    screen: {
      title: "Skills. 自动管理。",
      titlePrimary: "Skills.",
      titleSecondary: "自动管理。",
      eyebrow: "本地 AI 工作台",
      subtitle: "集中查看上下文占用，并管理 Skill 在各个 AI 开发工具中的开启状态。",
      unableToLoadSkills: (message: string) => `无法加载 Skill：${message}`,
    },
    sections: {
      inventoryStatistics: "Skill 使用概况",
      skillsInUse: "正在使用的 Skill",
      skillsInUseDescription: "查看每个 Skill 的资源占用，并控制它在已安装 AI 开发工具中的启停状态。",
      noSkillsInUse: "当前没有由 Skill Manager 管理的 Skill。",
      noMatchingSkills: "没有符合当前搜索和筛选条件的 Skill。",
      searchPlaceholder: "搜索 Skill",
      searchLabel: "按名称或简介搜索 Skill",
      filterAll: "全部",
      filterEnabled: "已开启",
      filterDisabled: "未开启",
    },
    stats: {
      inUse: "使用中",
      enabledBindings: "已开启连接",
      inUseDetail: "由 Skill Manager 统一管理",
      enabledBindingsDetail: "覆盖已安装的 AI 开发工具",
    },
  },
} satisfies LocalizedCopy<OverviewCopy>;

export function useOverviewCopy(): OverviewCopy {
  return useLocalizedCopy(overviewCopy);
}
