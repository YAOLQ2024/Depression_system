import type {
  AssessmentCatalogItem,
  AssessmentResult,
  AssessmentScaleDetail,
  AssessmentSession,
  ConsultationSession,
} from "../../types";
import type {
  ResultConsultationSummary,
  ResultConsultationSummarySection,
  ResultDetailPanelData,
  ResultModuleCard,
  ResultPageViewModel,
  ResultRiskFlag,
  ResultScaleBrief,
  ResultScaleItem,
  ResultTrendPoint,
} from "./types";

const CONSULTATION_SUMMARY_SECTION_DEFINITIONS = [
  {
    id: "chief-complaint",
    title: "主诉阶段摘要",
    sourceKey: "chief_complaint_stage_summary",
  },
  {
    id: "symptom-screening",
    title: "症状筛查阶段摘要",
    sourceKey: "symptom_screening_stage_summary",
  },
  {
    id: "high-risk-screening",
    title: "高风险筛查阶段摘要",
    sourceKey: "high_risk_screening_stage_summary",
  },
] as const;

type SummarySourceKey = (typeof CONSULTATION_SUMMARY_SECTION_DEFINITIONS)[number]["sourceKey"];

type ResultPageAdapterInput = {
  assessment: AssessmentSession | null;
  assessmentCatalog: AssessmentCatalogItem[];
  assessmentScaleDetails?: Record<string, AssessmentScaleDetail>;
  consultation: ConsultationSession | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim();
  return normalized ? normalized : null;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => asString(item))
    .filter((item): item is string => Boolean(item));
}

function normalizeRiskLevelLabel(value: unknown) {
  const normalized = asString(value);
  if (!normalized) {
    return null;
  }

  switch (normalized.toLowerCase()) {
    case "urgent":
      return "紧急风险";
    case "high":
      return "高风险";
    case "medium":
      return "中风险";
    case "low":
      return "低风险";
    default:
      return normalized;
  }
}

function formatDateTime(value?: string | null) {
  const normalized = asString(value);
  if (!normalized) {
    return null;
  }

  const candidate = new Date(normalized);
  if (Number.isNaN(candidate.getTime())) {
    return normalized;
  }

  const formatter = new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  return formatter.format(candidate).replace(/\//g, "-");
}

function formatTrendDate(value?: string | null) {
  const normalized = asString(value);
  if (!normalized) {
    return null;
  }

  const candidate = new Date(normalized);
  if (Number.isNaN(candidate.getTime())) {
    return normalized;
  }

  const month = String(candidate.getMonth() + 1).padStart(2, "0");
  const day = String(candidate.getDate()).padStart(2, "0");
  return `${month}-${day}`;
}

export function buildTrendPointsFromHistory(
  items: Array<{ completed_at?: string | null; score?: number | null }> | null | undefined,
): ResultTrendPoint[] {
  if (!Array.isArray(items)) {
    return [];
  }

  return items.reduce<ResultTrendPoint[]>((accumulator, item) => {
    const score = asNumber(item?.score);
    const date = formatTrendDate(item?.completed_at);
    if (score === null || !date) {
      return accumulator;
    }

    accumulator.push({ date, score });
    return accumulator;
  }, []);
}

function truncateText(value: string, maxLength = 54) {
  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, Math.max(0, maxLength - 3))}...`;
}

function buildCatalogMap(catalog: AssessmentCatalogItem[]) {
  return new Map(catalog.map((item) => [item.slug, item] as const));
}

function dedupeScaleSlugs(slugs: Array<string | null | undefined>) {
  return slugs.filter((slug, index): slug is string => Boolean(slug) && slugs.indexOf(slug) === index);
}

function getFallbackScaleSlugs(
  assessment: AssessmentSession | null,
  consultation: ConsultationSession | null,
) {
  if (assessment?.required_scales?.length) {
    return assessment.required_scales;
  }

  if (consultation?.required_scales?.length) {
    return consultation.required_scales;
  }

  return asStringArray(asRecord(assessment?.scale_handoff_payload)?.required_scales);
}

function getOrderedScaleSlugs(
  assessment: AssessmentSession | null,
  consultation: ConsultationSession | null,
  results: AssessmentResult[],
) {
  const resultSlugs = results.map((item) => item.scale_slug);

  if (assessment?.selected_scales?.length) {
    return dedupeScaleSlugs([...assessment.selected_scales, ...resultSlugs]);
  }

  if (resultSlugs.length) {
    return dedupeScaleSlugs(resultSlugs);
  }

  const fallback = getFallbackScaleSlugs(assessment, consultation);
  const merged = [...fallback, ...resultSlugs];

  return dedupeScaleSlugs(merged);
}

function getFlattenedRiskFlags(assessment: AssessmentSession | null) {
  const aggregate = asRecord(assessment?.aggregate_payload);
  const aggregateFlags = aggregate?.flattened_risk_flags;

  if (Array.isArray(aggregateFlags)) {
    return aggregateFlags
      .map((item) => asRecord(item))
      .filter((item): item is Record<string, unknown> => Boolean(item))
      .map((item) => ({ ...item }));
  }

  return (assessment?.results || []).flatMap((result) =>
    (result.risk_flags || []).map((flag) => ({
      scale_slug: result.scale_slug,
      ...flag,
    })),
  );
}

/*
function joinAdviceLines(items: string[]) {
  return items.length ? items.join("；") : null;
}

*/
function joinAdviceLines(items: string[]) {
  return items.length ? items.join("；") : null;
}

function buildOverallRiskReason(riskSummary: Record<string, unknown> | null) {
  const riskExplanation = asRecord(riskSummary?.risk_explanation);
  const triggerSummaries = asStringArray(riskExplanation?.trigger_summaries);
  if (triggerSummaries.length) {
    const visibleSummaries = triggerSummaries.slice(0, 2);
    const suffix = triggerSummaries.length > visibleSummaries.length ? " 等信号" : "";
    return `触发原因：${visibleSummaries.join("；")}${suffix}`;
  }

  const explanationSummary = asString(riskExplanation?.summary);
  if (explanationSummary) {
    return explanationSummary;
  }

  if (Boolean(riskSummary?.requires_human_review)) {
    return "当前结果存在需要人工复核的安全风险信号，请结合高风险筛查与量表风险条目综合判断。";
  }

  return null;
}

function formatModuleScore(value: unknown) {
  const score = asNumber(value);
  if (score === null) {
    return null;
  }

  return `${score.toFixed(2)}分`;
}

function getScoreBreakdown(assessment: AssessmentSession | null) {
  const riskSummary = getAssessmentRiskSummary(assessment);
  return asRecord(asRecord(riskSummary?.risk_explanation)?.score_breakdown);
}

function getAssessmentModuleValue(assessment: AssessmentSession | null) {
  const scoreBreakdown = getScoreBreakdown(assessment);
  const scaleScore = asRecord(scoreBreakdown?.scale_score);
  const explicitModuleScore = formatModuleScore(scaleScore?.value);
  if (explicitModuleScore) {
    return explicitModuleScore;
  }

  const results = assessment?.results || [];
  if (results.length !== 1) {
    return null;
  }

  const [singleResult] = results;
  const directNormalizedScore = asNumber(singleResult?.normalized_score);
  if (directNormalizedScore !== null) {
    return formatModuleScore(directNormalizedScore);
  }

  const aggregate = asRecord(assessment?.aggregate_payload);
  const normalizedScores = asRecord(aggregate?.normalized_scores);
  const scaleResultMap = asRecord(aggregate?.scale_result_map);
  const slug = asString(singleResult?.scale_slug);

  if (slug) {
    const normalizedScoreFromMap = asNumber(normalizedScores?.[slug]);
    if (normalizedScoreFromMap !== null) {
      return formatModuleScore(normalizedScoreFromMap);
    }

    const aggregateResult = asRecord(scaleResultMap?.[slug]);
    const normalizedScoreFromAggregateResult = asNumber(aggregateResult?.normalized_score);
    if (normalizedScoreFromAggregateResult !== null) {
      return formatModuleScore(normalizedScoreFromAggregateResult);
    }
  }

  return null;
}

function getMultimodalModuleValue(assessment: AssessmentSession | null) {
  const scoreBreakdown = getScoreBreakdown(assessment);
  const multimodalScore = asRecord(scoreBreakdown?.multimodal_score);
  return formatModuleScore(multimodalScore?.value);
}

function getAssessmentRiskSummary(assessment: AssessmentSession | null) {
  const aggregate = asRecord(assessment?.aggregate_payload);
  const directSummary = asRecord(aggregate?.risk_summary);
  if (directSummary) {
    return directSummary;
  }

  const evaluation = asRecord(aggregate?.risk_evaluation);
  if (!evaluation) {
    return null;
  }

  const result = asRecord(evaluation.result);
  const frontDisplay = asRecord(result?.front_display);
  return {
    evaluation_id: asString(evaluation.evaluation_id),
    risk_level: asString(evaluation.risk_level),
    risk_level_label: asString(frontDisplay?.risk_level_label),
    depression_score: asNumber(evaluation.depression_score),
    depression_severity: asString(evaluation.depression_severity),
    depression_severity_label: asString(result?.depression_severity_label),
    requires_human_review: Boolean(evaluation.requires_human_review),
    front_display: frontDisplay,
    risk_explanation: asRecord(result?.risk_explanation),
    referral_recommendations: asStringArray(result?.referral_recommendations),
    lifestyle_suggestions: asStringArray(result?.lifestyle_suggestions),
  };
}

function getScaleScoreMethod(result: AssessmentResult) {
  const scoreDetails = asRecord(result.score_details);
  return asString(scoreDetails?.score_method);
}

function resolveScaleMaxScore(result: AssessmentResult, meta?: AssessmentCatalogItem | null) {
  const scoreDetails = asRecord(result.score_details);
  const normalization = asRecord(scoreDetails?.normalization);
  const normalizationMaximum = asNumber(normalization?.maximum);
  if (normalizationMaximum !== null) {
    return normalizationMaximum;
  }

  if (!meta?.answer_options?.length || !meta.item_count) {
    return null;
  }

  const optionScores = meta.answer_options
    .map((option) => asNumber(option.score))
    .filter((score): score is number => score !== null);

  if (!optionScores.length) {
    return null;
  }

  const scoreMethod = getScaleScoreMethod(result);

  if (scoreMethod === "sum_excluding_not_applicable") {
    const notApplicableValue = asNumber(scoreDetails?.not_applicable_value);
    const effectiveScores = optionScores.filter((score) => score !== notApplicableValue);
    if (effectiveScores.length) {
      return Math.max(...effectiveScores) * meta.item_count;
    }
  }

  const rawMaxScore = Math.max(...optionScores) * meta.item_count;
  if (scoreMethod === "standard_score") {
    const multiplier = asNumber(scoreDetails?.standard_score_multiplier) ?? 1.25;
    return Math.round(rawMaxScore * multiplier);
  }

  return rawMaxScore;
}

const DETAIL_QUESTION_PREFIXES: Record<string, string[]> = {
  sds: ["接下来进入SDS量表问诊环节，请根据您最近一星期的实际情况回答。"],
  sas: ["接下来进入SAS量表问诊环节，我会问您20个问题，请根据您最近一星期的实际感受，按照选项作答。"],
};

function sanitizeScaleItemLabel(slug: string, itemIndex: number, label?: string | null) {
  const normalizedLabel = asString(label);
  if (!normalizedLabel) {
    return "";
  }

  if (itemIndex !== 1) {
    return normalizedLabel;
  }

  const prefixes = DETAIL_QUESTION_PREFIXES[slug] || [];
  for (const prefix of prefixes) {
    if (normalizedLabel.startsWith(prefix)) {
      return normalizedLabel.slice(prefix.length).trim();
    }
  }

  return normalizedLabel;
}

function inferSocialFunctionSeverity(
  normalizedScore?: number | null,
  derivedScore?: number | null,
) {
  const basis = normalizedScore ?? (typeof derivedScore === "number" ? Math.max(0, Math.min(100, derivedScore * 5)) : null);
  if (basis === null) {
    return null;
  }

  if (basis >= 75) {
    return "重度社会功能受损";
  }

  if (basis >= 50) {
    return "中度社会功能受损";
  }

  if (basis >= 25) {
    return "轻度社会功能受损";
  }

  return "社会功能基本正常";
}

function resolveDisplaySeverity({
  slug,
  interpretationLabel,
  interpretationLevel,
  normalizedScore,
  derivedScore,
}: {
  slug: string;
  interpretationLabel?: string | null;
  interpretationLevel?: string | null;
  normalizedScore?: number | null;
  derivedScore?: number | null;
}) {
  const explicitSeverity = asString(interpretationLabel) || asString(interpretationLevel);
  if (explicitSeverity) {
    return explicitSeverity;
  }

  if (slug === "social-function") {
    return inferSocialFunctionSeverity(normalizedScore, derivedScore);
  }

  return null;
}

function buildScalePlaceholderItems(meta?: AssessmentCatalogItem | null): ResultScaleItem[] {
  if (!meta?.items?.length) {
    return [];
  }

  return meta.items.map((item) => ({
    no: item.index,
    label: sanitizeScaleItemLabel(meta.slug, item.index, item.question_text || item.text),
    answerLabel: "加载中",
  }));
}

function formatItemScoreLabel(value: number) {
  if (value > 0) {
    return `+${value}分`;
  }

  if (value < 0) {
    return `${value}分`;
  }

  return "0分";
}

function buildScaleItemScoreMeta(
  detail: AssessmentScaleDetail,
  result: AssessmentResult,
  item: AssessmentScaleDetail["items"][number],
) {
  const selectedScore = asNumber(item.selected_option_score);
  if (selectedScore === null) {
    return {
      effectiveScore: null,
      effectiveScoreLabel: null,
      effectiveScoreTone: null,
      effectiveScoreHint: null,
    };
  }

  const scoreDetails = asRecord(result.score_details);
  const scoreMethod = getScaleScoreMethod(result);

  if (scoreMethod === "sum_excluding_not_applicable") {
    const notApplicableValue = asNumber(scoreDetails?.not_applicable_value);
    if (notApplicableValue !== null && selectedScore === notApplicableValue) {
      return {
        effectiveScore: null,
        effectiveScoreLabel: "不计分",
        effectiveScoreTone: "excluded" as const,
        effectiveScoreHint: "不适用项",
      };
    }
  }

  let effectiveScore = selectedScore;
  let effectiveScoreHint: string | null = null;

  if (scoreMethod === "standard_score") {
    const reverseScoredItems = new Set(asStringArray(scoreDetails?.reverse_scored_items));
    if (reverseScoredItems.has(item.item_id)) {
      const optionScores = detail.answer_options
        .map((option) => asNumber(option.score))
        .filter((score): score is number => score !== null);

      if (optionScores.length) {
        const minimumScore = Math.min(...optionScores);
        const maximumScore = Math.max(...optionScores);
        effectiveScore = maximumScore + minimumScore - selectedScore;
        effectiveScoreHint = "反向计分";
      }
    }
  }

  let effectiveScoreTone: ResultScaleItem["effectiveScoreTone"] = "neutral";
  if (effectiveScore > 0) {
    effectiveScoreTone = "positive";
  } else if (effectiveScore < 0) {
    effectiveScoreTone = "negative";
  }

  return {
    effectiveScore,
    effectiveScoreLabel: formatItemScoreLabel(effectiveScore),
    effectiveScoreTone,
    effectiveScoreHint,
  };
}

function buildScaleItemsFromDetail(
  detail: AssessmentScaleDetail,
  result: AssessmentResult,
): ResultScaleItem[] {
  return detail.items.map((item) => ({
    ...buildScaleItemScoreMeta(detail, result, item),
    no: item.item_index,
    label: sanitizeScaleItemLabel(detail.scale_slug, item.item_index, item.question_text),
    answerLabel: asString(item.selected_option_label),
    answerScore: asNumber(item.selected_option_score),
    answerSource: asString(item.answer_source),
    transcriptText: asString(item.transcript_text),
  }));
}

function buildScaleRiskFlags(result: AssessmentResult): ResultRiskFlag[] {
  return (result.risk_flags || []).reduce<ResultRiskFlag[]>((accumulator, flag) => {
      const flagRecord = asRecord(flag);
      if (!flagRecord) {
        return accumulator;
      }

      const flagCode = asString(flagRecord.flag);
      const label = asString(flagRecord.label);
      if (!flagCode || !label) {
        return accumulator;
      }

      accumulator.push({
        flag: flagCode,
        label,
        itemId: asString(flagRecord.item_id),
        scoreValue: asNumber(flagRecord.score_value),
      });
      return accumulator;
    }, []);
}

function getAnswerSummary(result: AssessmentResult) {
  const scoreDetails = asRecord(result.score_details);
  const answerSummary = asRecord(scoreDetails?.answer_summary);
  return {
    answeredItemCount: asNumber(answerSummary?.answered_item_count),
    configuredItemCount: asNumber(answerSummary?.configured_item_count),
  };
}

function getVerificationStatus(result: AssessmentResult) {
  const scoreDetails = asRecord(result.score_details);
  return asString(scoreDetails?.verification_status);
}

function getScoreMethodLabel(result: AssessmentResult) {
  const scoreMethod = getScaleScoreMethod(result);
  switch (scoreMethod) {
    case "sum":
      return "累计得分";
    case "standard_score":
      return "标准分";
    case "sum_excluding_not_applicable":
      return "排除不适用项累计";
    default:
      return null;
  }
}

function buildScaleRiskLabel({
  severity,
  riskFlags,
}: {
  severity?: string | null;
  riskFlags?: Array<Record<string, unknown>>;
}) {
  const normalizedSeverity = asString(severity) || "";
  const flags = riskFlags || [];
  const hasSelfHarmFlag = flags.some((flag) => asString(flag.flag) === "self_harm_positive");

  if (hasSelfHarmFlag) {
    return "重点关注";
  }

  if (normalizedSeverity.includes("重度") || normalizedSeverity.includes("危险")) {
    return "高风险";
  }

  if (normalizedSeverity.includes("中度") || normalizedSeverity.includes("关注")) {
    return "需关注";
  }

  if (normalizedSeverity.includes("轻度")) {
    return "建议观察";
  }

  if (normalizedSeverity.includes("正常") || normalizedSeverity.includes("无")) {
    return "低风险";
  }

  return "待补充";
}

function buildScaleInterpretation(
  result: AssessmentResult,
  meta?: AssessmentCatalogItem | null,
  severity?: string | null,
) {
  const scaleName = meta?.short_name || meta?.name || result.scale_slug;
  const normalizedSeverity = asString(severity);
  const score = result.derived_score;

  if (normalizedSeverity) {
    return `当前 ${scaleName} 结果提示为${normalizedSeverity}，本次得分 ${score} 分，建议结合临床访谈继续综合判断。`;
  }

  return `${scaleName} 已完成评估，本次得分 ${score} 分，正式结果解读待补充。`;
}

function buildScaleRiskHint({
  severity,
  riskFlags,
}: {
  severity?: string | null;
  riskFlags?: Array<Record<string, unknown>>;
}) {
  const normalizedSeverity = asString(severity) || "";
  const hasSelfHarmFlag = (riskFlags || []).some(
    (flag) => asString(flag.flag) === "self_harm_positive",
  );

  if (hasSelfHarmFlag) {
    return "量表中出现需要重点关注的风险条目，建议尽快联系专业人员进一步评估。";
  }

  if (normalizedSeverity.includes("重度") || normalizedSeverity.includes("危险")) {
    return "当前结果提示风险较高，建议尽快进行专业评估与干预。";
  }

  if (normalizedSeverity.includes("中度") || normalizedSeverity.includes("关注")) {
    return "当前结果提示存在需要关注的风险，建议持续观察并尽早寻求专业支持。";
  }

  if (normalizedSeverity.includes("轻度")) {
    return "当前结果提示存在轻度风险波动，建议保持跟踪并留意症状变化。";
  }

  if (normalizedSeverity.includes("正常") || normalizedSeverity.includes("无")) {
    return "当前结果未见明显风险信号，建议继续保持观察并结合日常功能变化综合判断。";
  }

  return "当前风险提示待结合后续规则进一步补充。";
}

function buildScaleBrief(
  slug: string,
  result: AssessmentResult | null,
  meta?: AssessmentCatalogItem | null,
): ResultScaleBrief {
  const severity = resolveDisplaySeverity({
    slug,
    interpretationLabel: result?.interpretation_label,
    interpretationLevel: result?.interpretation_level,
    normalizedScore: result?.normalized_score,
    derivedScore: result?.derived_score,
  });

  if (!result) {
    return {
      id: slug,
      name: meta?.short_name || meta?.code || slug,
      fullName: meta?.name || null,
      score: null,
      maxScore: null,
      scoreLabel: "待接入",
      severity: severity || "待评估",
    };
  }

  const maxScore = resolveScaleMaxScore(result, meta);
  return {
    id: slug,
    name: meta?.short_name || meta?.code || slug,
    fullName: meta?.name || null,
    score: result.derived_score,
    maxScore,
    scoreLabel: `${result.derived_score}分`,
    severity: severity || "待评估",
  };
}

function buildScaleDetail(
  slug: string,
  result: AssessmentResult | null,
  meta?: AssessmentCatalogItem | null,
  scaleDetail?: AssessmentScaleDetail | null,
): ResultDetailPanelData {
  if (!result) {
    return {
      id: slug,
      title: `${meta?.short_name || meta?.code || slug} 详细报告`,
      name: meta?.short_name || meta?.name || slug,
      fullName: meta?.name || null,
      completedAt: null,
      score: null,
      maxScore: null,
      normalizedScore: null,
      severity: "待评估",
      riskLabel: "待补充",
      interpretation: "当前量表结果待接入。",
      riskHint: "风险提示待接入。",
      clinicalAdvice: null,
      lifestyleAdvice: null,
      riskFlags: [],
      answeredItemCount: null,
      configuredItemCount: meta?.item_count || null,
      scoreMethodLabel: null,
      verificationStatus: null,
      itemResultsReady: false,
      itemResultsNotice: meta?.items?.length ? "详细作答明细加载中。" : null,
      history: [],
      items: buildScalePlaceholderItems(meta),
    };
  }

  const answerSummary = getAnswerSummary(result);
  const verificationStatus = getVerificationStatus(result);
  const riskFlags = buildScaleRiskFlags(result);
  const placeholderItems = buildScalePlaceholderItems(meta);
  const detailItems = scaleDetail ? buildScaleItemsFromDetail(scaleDetail, result) : placeholderItems;
  const itemResultsReady = Boolean(scaleDetail);
  const severity = resolveDisplaySeverity({
    slug,
    interpretationLabel: scaleDetail?.interpretation_label ?? result.interpretation_label,
    interpretationLevel: scaleDetail?.interpretation_level ?? result.interpretation_level,
    normalizedScore: scaleDetail?.normalized_score ?? result.normalized_score,
    derivedScore: scaleDetail?.derived_score ?? result.derived_score,
  });

  return {
    id: slug,
    title: `${meta?.short_name || meta?.code || slug} 详细报告`,
    name: meta?.short_name || meta?.name || slug,
    fullName: meta?.name || null,
    completedAt: formatDateTime(scaleDetail?.completed_at || result.completed_at),
    score: scaleDetail?.derived_score ?? result.derived_score,
    maxScore: resolveScaleMaxScore(result, meta),
    normalizedScore: scaleDetail?.normalized_score ?? result.normalized_score ?? null,
    severity: severity || "待评估",
    riskLabel: buildScaleRiskLabel({ severity, riskFlags: result.risk_flags }),
    interpretation: buildScaleInterpretation(result, meta, severity),
    riskHint: buildScaleRiskHint({ severity, riskFlags: result.risk_flags }),
    // Reserved for the future assessment detail / risk-service advice contract.
    clinicalAdvice: null,
    lifestyleAdvice: null,
    riskFlags,
    answeredItemCount: scaleDetail?.answered_item_count ?? answerSummary.answeredItemCount,
    configuredItemCount:
      scaleDetail?.configured_item_count ??
      answerSummary.configuredItemCount ??
      meta?.item_count ??
      null,
    scoreMethodLabel: getScoreMethodLabel(result),
    verificationStatus,
    itemResultsReady,
    itemResultsNotice: itemResultsReady ? null : placeholderItems.length ? "详细作答明细加载中。" : null,
    // Reserved for the future per-scale history contract.
    history: [],
    items: detailItems,
  };
}

function readConsultationSummaryField(
  source: Record<string, unknown> | ConsultationSession | null,
  key: SummarySourceKey | "digital_human_consultation_summary",
) {
  if (!source) {
    return null;
  }

  if (key in source) {
    return asString(source[key]);
  }

  return null;
}

function hasConsultationSummaryContent(
  source: Record<string, unknown> | ConsultationSession | null,
) {
  if (!source) {
    return false;
  }

  if (readConsultationSummaryField(source, "digital_human_consultation_summary")) {
    return true;
  }

  return CONSULTATION_SUMMARY_SECTION_DEFINITIONS.some((definition) =>
    Boolean(readConsultationSummaryField(source, definition.sourceKey)),
  );
}

function getPreferredConsultationSummarySource(
  assessment: AssessmentSession | null,
  consultation: ConsultationSession | null,
) {
  const handoffSource = asRecord(assessment?.scale_handoff_payload);
  if (hasConsultationSummaryContent(handoffSource)) {
    return handoffSource;
  }
  return consultation;
}

function buildConsultationSummary(
  assessment: AssessmentSession | null,
  consultation: ConsultationSession | null,
  catalogMap: Map<string, AssessmentCatalogItem>,
): ResultConsultationSummary | null {
  const source = getPreferredConsultationSummarySource(assessment, consultation);
  if (!source) {
    return null;
  }

  const sections = CONSULTATION_SUMMARY_SECTION_DEFINITIONS.reduce<ResultConsultationSummarySection[]>(
    (accumulator, definition) => {
      const content = readConsultationSummaryField(source, definition.sourceKey);
      if (!content) {
        return accumulator;
      }

      accumulator.push({
        id: definition.id,
        title: definition.title,
        content,
      });
      return accumulator;
    },
    [],
  );

  const overallSummary =
    readConsultationSummaryField(source, "digital_human_consultation_summary") ||
    sections.map((section) => section.content).join("；");

  if (!overallSummary && !sections.length) {
    return null;
  }

  const linkedScales = getOrderedScaleSlugs(assessment, consultation, assessment?.results || []);
  const linkedScaleLabels = linkedScales.map((slug) => {
    const meta = catalogMap.get(slug);
    return meta?.short_name || meta?.code || slug;
  });

  return {
    id: "consultation-summary",
    title: "咨询会话摘要报告",
    description: overallSummary
      ? truncateText(overallSummary, 56)
      : "咨询会话摘要已生成，可查看阶段性总结。",
    overallSummary: overallSummary || "咨询会话摘要待补充。",
    sections,
    linkedScales,
    linkedScaleLabels,
  };
}

/*
function buildAssessmentModuleDescription(
  scaleCount: number,
  flattenedRiskFlags: Array<Record<string, unknown>>,
  riskSummary: Record<string, unknown> | null,
) {
  if (!scaleCount) {
    return "量表结果待接入。";
  }

  if (riskSummary) {
    return `宸插畬鎴?${scaleCount} 浠介噺琛ㄥ苟鐢熸垚缁煎悎鍐崇瓥缁撴灉銆俙;
  }

  if (flattenedRiskFlags.length) {
    return `已完成 ${scaleCount} 份量表，识别到 ${flattenedRiskFlags.length} 项风险标记。`;
  }

  return `已完成 ${scaleCount} 份量表，单量表结果已生成。`;
}

function buildMultimodalModuleDescription(
  assessment: AssessmentSession | null,
  consultation: ConsultationSession | null,
  riskSummary: Record<string, unknown> | null,
) {
  const aggregate = asRecord(assessment?.aggregate_payload);
  const finalBundle = asRecord(aggregate?.multimodal_feature_bundle);
  const multimodalSessionId =
    asString(assessment?.multimodal_session_id) || asString(consultation?.multimodal_session_id);

  if (riskSummary && finalBundle) {
    return "澶氭ā鎬佺粓鎬佺壒寰佸凡鑱氬悎骞剁撼鍏ョ患鍚堣瘎鍒嗐€?";
  }

  if (finalBundle) {
    return "澶氭ā鎬佺粓鎬佺壒寰佸凡鑱氬悎锛岀瓑寰呭喅绛栬绠椼€?";
  }

  return multimodalSessionId
    ? "多模态会话已完成绑定，综合评分待接入。"
    : "多模态综合结果待接入。";
}

*/
function buildAssessmentModuleDescription(
  scaleCount: number,
  flattenedRiskFlags: Array<Record<string, unknown>>,
  riskSummary: Record<string, unknown> | null,
) {
  if (!scaleCount) {
    return "量表结果待接入。";
  }

  if (riskSummary) {
    return `已完成 ${scaleCount} 份量表并生成综合决策结果。`;
  }

  if (flattenedRiskFlags.length) {
    return `已完成 ${scaleCount} 份量表，识别到 ${flattenedRiskFlags.length} 项风险标记。`;
  }

  return `已完成 ${scaleCount} 份量表，单量表结果已生成。`;
}

function buildMultimodalModuleDescription(
  assessment: AssessmentSession | null,
  consultation: ConsultationSession | null,
  riskSummary: Record<string, unknown> | null,
) {
  const aggregate = asRecord(assessment?.aggregate_payload);
  const finalBundle = asRecord(aggregate?.multimodal_feature_bundle);
  const multimodalSessionId =
    asString(assessment?.multimodal_session_id) || asString(consultation?.multimodal_session_id);

  if (riskSummary && finalBundle) {
    return "多模态终态特征已聚合并纳入综合评分。";
  }

  if (finalBundle) {
    return "多模态终态特征已聚合，等待决策评分。";
  }

  return multimodalSessionId
    ? "多模态观察已完成绑定，综合结果待补充。"
    : "多模态综合结果待接入。";
}

function buildModules({
  assessment,
  consultation,
  consultationSummary,
  scaleCount,
  flattenedRiskFlags,
  riskSummary,
  assessmentModuleValue,
  multimodalModuleValue,
}: {
  assessment: AssessmentSession | null;
  consultation: ConsultationSession | null;
  consultationSummary: ResultConsultationSummary | null;
  scaleCount: number;
  flattenedRiskFlags: Array<Record<string, unknown>>;
  riskSummary: Record<string, unknown> | null;
  assessmentModuleValue?: string | null;
  multimodalModuleValue?: string | null;
}): ResultModuleCard[] {
  return [
    {
      id: "consultation-summary",
      name: "问诊总结",
      description: consultationSummary ? "本轮主诉、症状与风险表达已纳入综合评估。" : "问诊摘要待接入。",
      actionLabel: consultationSummary ? "查看详情" : null,
      tone: "blue",
    },
    {
      id: "assessment-session",
      name: "量表结果",
      value: assessmentModuleValue,
      description: buildAssessmentModuleDescription(scaleCount, flattenedRiskFlags, riskSummary),
      tone: "indigo",
    },
    {
      id: "multimodal-session",
      name: "多模态观察",
      value: multimodalModuleValue,
      description: buildMultimodalModuleDescription(assessment, consultation, riskSummary),
      tone: "emerald",
    },
  ];
}

export function buildResultPageViewModel({
  assessment,
  assessmentCatalog,
  assessmentScaleDetails = {},
  consultation,
}: ResultPageAdapterInput): ResultPageViewModel {
  const catalogMap = buildCatalogMap(assessmentCatalog);
  const results = assessment?.results || [];
  const scaleSlugs = getOrderedScaleSlugs(assessment, consultation, results);
  const resultMap = new Map(results.map((result) => [result.scale_slug, result] as const));
  const flattenedRiskFlags = getFlattenedRiskFlags(assessment);
  const riskSummary = getAssessmentRiskSummary(assessment);
  const riskFrontDisplay = asRecord(riskSummary?.front_display);
  const assessmentModuleValue = getAssessmentModuleValue(assessment);
  const multimodalModuleValue = getMultimodalModuleValue(assessment);
  const overallScore = asNumber(riskSummary?.depression_score);
  const overallSeverity =
    asString(riskSummary?.depression_severity_label) ||
    asString(riskSummary?.depression_severity);
  const overallRiskLevel =
    asString(riskSummary?.risk_level_label) ||
    asString(riskFrontDisplay?.risk_level_label) ||
    normalizeRiskLevelLabel(riskSummary?.risk_level);
  const overallRiskReason = buildOverallRiskReason(riskSummary);
  const clinicalAdvice = joinAdviceLines(asStringArray(riskSummary?.referral_recommendations));
  const lifestyleAdvice = joinAdviceLines(asStringArray(riskSummary?.lifestyle_suggestions));
  const consultationSummary = buildConsultationSummary(assessment, consultation, catalogMap);
  const scales = scaleSlugs.map((slug) => buildScaleBrief(slug, resultMap.get(slug) || null, catalogMap.get(slug)));

  const scaleDetails = scaleSlugs.reduce<Record<string, ResultDetailPanelData>>((accumulator, slug) => {
    accumulator[slug] = buildScaleDetail(
      slug,
      resultMap.get(slug) || null,
      catalogMap.get(slug),
      assessmentScaleDetails[slug] || null,
    );
    return accumulator;
  }, {});

  return {
    hasAssessment: Boolean(assessment),
    assessmentSessionId: assessment?.session_id || null,
    encounterSessionId: assessment?.encounter_session_id || consultation?.encounter_session_id || null,
    status: assessment?.status || "idle",
    defaultScaleId: scales[0]?.id || null,
    // Reserved for the future top-level risk-service contract.
    overallScore,
    overallScorePending: !riskSummary,
    /*
    overallSeverity: "待接入",
    overallSeverityPending: true,
    */
    /*
    ...{
      overallSeverity: overallSeverity || "寰呮帴鍏?",
      overallSeverityPending: !riskSummary,
    },
    */
    ...{
      overallSeverity: overallSeverity || "待接入",
      overallSeverityPending: !riskSummary,
      overallRiskLevel: overallRiskLevel || "待接入",
      overallRiskLevelPending: !riskSummary,
      overallRiskReason,
    },
    modules: buildModules({
      assessment,
      consultation,
      consultationSummary,
      scaleCount: scales.filter((item) => typeof item.score === "number").length,
      flattenedRiskFlags,
      riskSummary,
      assessmentModuleValue,
      multimodalModuleValue,
    }),
    scales,
    scaleDetails,
    consultationSummary,
    // Reserved for the future top-level risk-service advice contract.
    /*
    clinicalAdvice: null,
    lifestyleAdvice: null,
    */
    ...{
      clinicalAdvice,
      lifestyleAdvice,
    },
    flattenedRiskFlags,
  };
}
