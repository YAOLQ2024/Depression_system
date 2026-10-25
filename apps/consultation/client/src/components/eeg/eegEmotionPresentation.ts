import type { MultimodalRankedLabel } from "../../types";

export const EEG_EMOTION_ORDER = ["消极", "中性", "积极"] as const;

export type EegEmotionLabel = (typeof EEG_EMOTION_ORDER)[number];

export type EegEmotionDistributionItem = {
  label: EegEmotionLabel;
  score: number;
};

export type DominantHeadPresentation = EegEmotionDistributionItem & {
  percentage: number;
  accentColor: string;
  highlightColor: string;
  imageSrc: string;
  scale: number;
  imageOpacity: number;
  brightness: number;
  glowAlpha: number;
};

const EEG_EMOTION_CONFIG: Record<
  EegEmotionLabel,
  {
    accentColor: string;
    highlightColor: string;
    imageSrc: string;
  }
> = {
  消极: {
    accentColor: "#D98B79",
    highlightColor: "#F0C3B7",
    imageSrc: "/eeg-emotion/mirror/head_negative.png",
  },
  中性: {
    accentColor: "#82AEE8",
    highlightColor: "#D2E3F7",
    imageSrc: "/eeg-emotion/mirror/head_neutral.png",
  },
  积极: {
    accentColor: "#48D6B0",
    highlightColor: "#B6F2DF",
    imageSrc: "/eeg-emotion/mirror/head_positive.png",
  },
};

function clampNumber(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function normalizeScore(score?: number | null) {
  if (typeof score !== "number" || Number.isNaN(score)) {
    return 0;
  }
  const resolved = score > 1 ? score / 100 : score;
  return clampNumber(resolved, 0, 1);
}

export function clampToPercent(score?: number | null) {
  return Math.round(normalizeScore(score) * 100);
}

export function withAlpha(hexColor: string, alpha: number) {
  const normalized = hexColor.replace("#", "");
  if (normalized.length !== 6) {
    return hexColor;
  }
  const red = Number.parseInt(normalized.slice(0, 2), 16);
  const green = Number.parseInt(normalized.slice(2, 4), 16);
  const blue = Number.parseInt(normalized.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${clampNumber(alpha, 0, 1)})`;
}

export function getEegEmotionConfig(label: EegEmotionLabel) {
  return EEG_EMOTION_CONFIG[label];
}

export function getDefaultEegEmotionConfig() {
  return {
    accentColor: "#94a3b8",
    highlightColor: "#e2e8f0",
    imageSrc: EEG_EMOTION_CONFIG["中性"].imageSrc,
  };
}

export function coerceEegEmotionLabel(label?: string | null): EegEmotionLabel | null {
  if (!label) {
    return null;
  }
  return EEG_EMOTION_ORDER.find((candidate) => candidate === label) ?? null;
}

export function normalizeEegEmotionDistribution(labels?: MultimodalRankedLabel[] | null): EegEmotionDistributionItem[] {
  const scoreByLabel = new Map<string, number>();
  for (const item of labels || []) {
    if (!item?.label) {
      continue;
    }
    scoreByLabel.set(item.label, normalizeScore(item.score));
  }

  return EEG_EMOTION_ORDER.map((label) => ({
    label,
    score: scoreByLabel.get(label) ?? 0,
  }));
}

export function hasEegEmotionResult(
  distribution: EegEmotionDistributionItem[],
  primaryLabel?: string | null,
) {
  return Boolean(coerceEegEmotionLabel(primaryLabel) || distribution.some((item) => item.score > 0));
}

export function resolvePrimaryEegEmotionLabel(
  distribution: EegEmotionDistributionItem[],
  primaryLabel?: string | null,
) {
  const explicitLabel = coerceEegEmotionLabel(primaryLabel);
  if (explicitLabel) {
    return explicitLabel;
  }
  const sorted = [...distribution].sort((left, right) => right.score - left.score);
  return sorted[0]?.score > 0 ? sorted[0].label : null;
}

export function getEegEmotionScore(distribution: EegEmotionDistributionItem[], label: EegEmotionLabel) {
  return distribution.find((item) => item.label === label)?.score ?? 0;
}

export function resolveEegEmotionStatusLabel(deviceStatus?: string | null, errorMessage?: string | null) {
  if (errorMessage) {
    return "识别失败";
  }

  switch (deviceStatus) {
    case "disabled":
    case "idle":
    case "disconnected":
      return "设备未连接";
    case "dependency_missing":
      return "设备未就绪";
    default:
      return "等待 EEG 分类结果";
  }
}

export function resolveDominantHeadPresentation(
  distribution: EegEmotionDistributionItem[],
  primaryLabel?: string | null,
  primaryScore?: number | null,
): DominantHeadPresentation | null {
  const resolvedPrimaryLabel = resolvePrimaryEegEmotionLabel(distribution, primaryLabel);
  if (!resolvedPrimaryLabel) {
    return null;
  }

  const explicitPrimaryLabel = coerceEegEmotionLabel(primaryLabel);
  const score =
    explicitPrimaryLabel === resolvedPrimaryLabel && typeof primaryScore === "number" && !Number.isNaN(primaryScore)
      ? normalizeScore(primaryScore)
      : getEegEmotionScore(distribution, resolvedPrimaryLabel);
  const config = getEegEmotionConfig(resolvedPrimaryLabel);

  return {
    label: resolvedPrimaryLabel,
    score,
    percentage: clampToPercent(score),
    accentColor: config.accentColor,
    highlightColor: config.highlightColor,
    imageSrc: config.imageSrc,
    scale: clampNumber(1 + score * 0.012, 1, 1.012),
    imageOpacity: clampNumber(0.9 + score * 0.1, 0.9, 1),
    brightness: clampNumber(0.96 + score * 0.05, 0.96, 1.01),
    glowAlpha: clampNumber(0.1 + score * 0.08, 0.1, 0.18),
  };
}
