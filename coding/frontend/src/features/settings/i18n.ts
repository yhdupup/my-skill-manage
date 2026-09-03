import { useLocalizedCopy, type CopyShape, type LocalizedCopy } from "../../i18n";

const englishSettingsCopy = {
  title: "Settings",
  subtitle: "Context estimates and per-harness discovery.",
  loading: "Loading settings",
  harnesses: {
    heading: "Harness roots",
    detected: "Detected on this machine",
    notDetected: "Not detected on this machine",
    enableSupport: (label: string) => `Enable ${label} support`,
    saving: "Saving...",
  },
  errors: {
    unableToLoad: "Unable to load settings.",
    unableToUpdateHarnessSupport: "Unable to update harness support.",
    unableToUpdateContextWindow: "Unable to save the context window.",
  },
  referenceContextWindow: {
    heading: "Reference context window",
    description: "Approximate size used to estimate each Skill's context usage. Adjust to match your model.",
    tooltip:
      "Estimate only. Different model tokenizers produce different counts; the value here is a planning aid, not a hard budget.",
    label: "Reference window in tokens",
    placeholder: "e.g. 128000",
    save: "Save",
    saving: "Saving...",
    saved: "Saved",
    invalidPositiveInteger: "Enter a positive whole number.",
    tooSmall: "Use at least 1 token.",
  },
} as const;

export type SettingsCopy = CopyShape<typeof englishSettingsCopy>;

export const settingsCopy = {
  en: englishSettingsCopy,
  "zh-CN": {
    title: "设置",
    subtitle: "上下文估算和各 AI 开发工具的发现设置。",
    loading: "正在加载设置",
    harnesses: {
      heading: "AI 开发工具根目录",
      detected: "已在本机检测到",
      notDetected: "未在本机检测到",
      enableSupport: (label: string) => `启用 ${label}`,
      saving: "保存中...",
    },
    errors: {
      unableToLoad: "无法加载设置。",
      unableToUpdateHarnessSupport: "无法更新 AI 开发工具的支持状态。",
      unableToUpdateContextWindow: "无法保存参考上下文窗口。",
    },
    referenceContextWindow: {
      heading: "参考上下文窗口",
      description: "用于估算每个技能上下文占用的近似大小，可按常用模型调整。",
      tooltip: "仅为预计值，不同模型的分词器计数会存在差异；这里是一个规划辅助，不是硬性预算。",
      label: "参考窗口（令牌数）",
      placeholder: "例如 128000",
      save: "保存",
      saving: "保存中...",
      saved: "已保存",
      invalidPositiveInteger: "请输入正整数。",
      tooSmall: "令牌数必须至少为 1。",
    },
  },
} satisfies LocalizedCopy<SettingsCopy>;

export function useSettingsCopy(): SettingsCopy {
  return useLocalizedCopy(settingsCopy);
}
