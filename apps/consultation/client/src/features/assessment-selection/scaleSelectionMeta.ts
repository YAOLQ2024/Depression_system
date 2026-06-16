import type { AssessmentCatalogItem } from "../../types";

export const ACTIVE_SCALE_SELECTION_ORDER = [
  "phq9",
  "sds",
  "sas",
  "social-function",
] as const;

export type ActiveScaleSelectionSlug = (typeof ACTIVE_SCALE_SELECTION_ORDER)[number];

export type ScaleSelectionMeta = {
  description: string;
  estimatedDurationText: string;
};

export const SCALE_SELECTION_META: Record<ActiveScaleSelectionSlug, ScaleSelectionMeta> = {
  phq9: {
    description: "用于了解最近两周情绪、兴趣和精力方面的变化。",
    estimatedDurationText: "约 2-3 分钟",
  },
  sds: {
    description: "用于了解最近一周抑郁体验对日常状态的影响。",
    estimatedDurationText: "约 4-5 分钟",
  },
  sas: {
    description: "用于了解最近一周焦虑、紧张和身体不适体验。",
    estimatedDurationText: "约 4-5 分钟",
  },
  "social-function": {
    description: "用于了解情绪问题对学习、工作和社交功能的影响。",
    estimatedDurationText: "约 2-3 分钟",
  },
};

const ACTIVE_SCALE_SELECTION_INDEX = new Map(
  ACTIVE_SCALE_SELECTION_ORDER.map((slug, index) => [slug, index] as const),
);

export type AssessmentSelectionCatalogItem = AssessmentCatalogItem & {
  slug: ActiveScaleSelectionSlug;
  description: string;
  estimatedDurationText: string;
  selectionOrder: number;
};

export function isActiveScaleSelectionSlug(value: string): value is ActiveScaleSelectionSlug {
  return ACTIVE_SCALE_SELECTION_ORDER.includes(value as ActiveScaleSelectionSlug);
}

export function normalizeSelectedScaleOrder(selectedScales: string[]): ActiveScaleSelectionSlug[] {
  const normalizedSelection = new Set<ActiveScaleSelectionSlug>();
  for (const rawSlug of selectedScales) {
    const slug = String(rawSlug || "").trim();
    if (!isActiveScaleSelectionSlug(slug)) {
      continue;
    }
    normalizedSelection.add(slug);
  }
  return ACTIVE_SCALE_SELECTION_ORDER.filter((slug) => normalizedSelection.has(slug));
}

export function buildAssessmentSelectionCatalog(
  catalog: AssessmentCatalogItem[],
): AssessmentSelectionCatalogItem[] {
  return catalog
    .filter((item): item is AssessmentCatalogItem & { slug: ActiveScaleSelectionSlug } =>
      isActiveScaleSelectionSlug(String(item.slug || "").trim()),
    )
    .sort(
      (left, right) =>
        (ACTIVE_SCALE_SELECTION_INDEX.get(left.slug) ?? Number.MAX_SAFE_INTEGER) -
        (ACTIVE_SCALE_SELECTION_INDEX.get(right.slug) ?? Number.MAX_SAFE_INTEGER),
    )
    .map((item) => ({
      ...item,
      description: SCALE_SELECTION_META[item.slug].description,
      estimatedDurationText: SCALE_SELECTION_META[item.slug].estimatedDurationText,
      selectionOrder: (ACTIVE_SCALE_SELECTION_INDEX.get(item.slug) ?? 0) + 1,
    }));
}
