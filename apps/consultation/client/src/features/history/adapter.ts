import type {
  EncounterAssessmentDetail,
  EncounterAssessmentResult,
  EncounterConsultationDetail,
  EncounterDetailData,
} from "../../services/api/contracts";
import type {
  AssessmentResult,
  AssessmentScaleDetail,
  AssessmentSession,
  ConsultationSession,
  ConsultationSubtitleHistoryEntry,
} from "../../types";

export type HistoryInsightItem = {
  label: string;
  value: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
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

function dedupeScaleSlugs(slugs: Array<string | null | undefined>) {
  return slugs.filter((slug, index): slug is string => Boolean(slug) && slugs.indexOf(slug) === index);
}

const INSIGHT_LABEL_MAP: Record<string, string> = {
  // 症状相关
  symptom: "症状",
  symptom_type: "症状类型",
  symptom_name: "症状名称",
  symptom_onset: "症状出现时间",
  symptom_duration: "症状持续时间",
  symptom_severity: "症状严重程度",
  symptom_frequency: "症状频率",
  symptom_description: "症状描述",
  chief_complaint: "主诉",
  chief_complaint_summary: "主诉摘要",
  // 情绪/心理
  mood: "情绪状态",
  mood_change: "情绪变化",
  anxiety: "焦虑",
  depression: "抑郁",
  sleep_quality: "睡眠质量",
  sleep: "睡眠",
  appetite: "食欲",
  energy: "精力",
  interest: "兴趣",
  concentration: "注意力",
  self_esteem: "自尊",
  guilt: "内疚",
  hopelessness: "无望感",
  suicidal_ideation: "自杀意念",
  self_harm: "自伤",
  self_harm_behavior: "自伤行为",
  // 风险相关
  risk_level: "风险等级",
  risk_factor: "风险因素",
  risk_flag: "风险标记",
  risk_description: "风险描述",
  protective_factor: "保护因素",
  alert_level: "警报等级",
  outcome: "处置结果",
  // 筛查结果
  recent_stressor: "近期压力源",
  compulsive_behavior: "强迫行为",
  manic_episode_indicator: "躁狂发作指标",
  suicide_plan: "自杀计划",
  acute_support_state: "紧急支持状态",
  primary_concern: "主要诉求",
  // 状态值翻译
  available: "有",
  unknown: "未知",
  low: "低",
  medium: "中",
  high: "高",
  safe_to_continue: "可继续",
  requires_intervention: "需要干预",
  // 诊断/评估
  diagnosis: "诊断",
  diagnosis_label: "诊断标签",
  severity: "严重程度",
  severity_level: "严重程度",
  interpretation: "解读",
  interpretation_label: "解读标签",
  score: "评分",
  total_score: "总分",
  // 个人信息
  age: "年龄",
  gender: "性别",
  marital_status: "婚姻状况",
  occupation: "职业",
  education: "学历",
  family_history: "家族史",
  medical_history: "病史",
  medication: "用药情况",
  treatment_history: "治疗史",
  // 时间
  onset_time: "发病时间",
  duration: "持续时间",
  first_episode: "首次发作",
  episode_count: "发作次数",
  last_episode: "最近发作",
  // 其他
  note: "备注",
  notes: "备注",
  summary: "摘要",
  conclusion: "结论",
  suggestion: "建议",
  follow_up: "随访",
  lifestyle: "生活方式",
  social_support: "社会支持",
  trigger: "诱因",
  stressor: "压力源",
  coping: "应对方式",
};

function formatInsightLabel(key: string) {
  const normalized = key.replace(/[_-]+/g, "_").trim().toLowerCase();
  return INSIGHT_LABEL_MAP[normalized] || INSIGHT_LABEL_MAP[key] || key.replace(/[_-]+/g, " ").trim() || key;
}

const INSIGHT_VALUE_MAP: Record<string, string> = {
  available: "有",
  unavailable: "无",
  unknown: "未知",
  none: "无",
  low: "低",
  medium: "中",
  high: "高",
  safe_to_continue: "可继续",
  requires_intervention: "需要干预",
  "不知道": "不知道",
};

function formatInsightTranslatedValue(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/[_-]+/g, "_");
  return INSIGHT_VALUE_MAP[normalized] || INSIGHT_VALUE_MAP[value.trim()] || value;
}

function formatInsightValue(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "string") {
    const normalized = value.trim();
    return normalized ? formatInsightTranslatedValue(normalized) : null;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  if (Array.isArray(value)) {
    const parts = value
      .map((item) => formatInsightValue(item))
      .filter((item): item is string => Boolean(item));
    return parts.length ? parts.join("，") : null;
  }

  const record = asRecord(value);
  if (!record) {
    return null;
  }

  const entries = Object.entries(record)
    .map(([nestedKey, nestedValue]) => {
      const nestedText = formatInsightValue(nestedValue);
      return nestedText ? `${formatInsightLabel(nestedKey)}: ${nestedText}` : null;
    })
    .filter((item): item is string => Boolean(item));

  return entries.length ? entries.join("；") : null;
}

function resolveAssessmentScaleHandoffPayload(
  assessment: EncounterAssessmentDetail | null,
  consultation: EncounterConsultationDetail | null,
) {
  const aggregatePayload = asRecord(assessment?.aggregate_payload);
  return (
    asRecord(assessment?.scale_handoff_payload) ||
    asRecord(aggregatePayload?.source_handoff) ||
    asRecord(consultation?.scale_handoff_payload) ||
    {}
  );
}

function buildAssessmentResults(
  results: EncounterAssessmentResult[],
  aggregatePayload?: Record<string, unknown> | null,
): AssessmentResult[] {
  const scaleResultMap = asRecord(aggregatePayload?.scale_result_map);

  return results.map((result) => {
    const aggregateResult = asRecord(scaleResultMap?.[result.scale_slug]);

    return {
      scale_slug: result.scale_slug,
      raw_score: result.raw_score,
      derived_score: result.derived_score,
      normalized_score:
        result.normalized_score ??
        (typeof aggregateResult?.normalized_score === "number"
          ? aggregateResult.normalized_score
          : null),
      interpretation_level:
        result.interpretation_level || asString(aggregateResult?.interpretation_level),
      interpretation_label:
        result.interpretation_label || asString(aggregateResult?.interpretation_label),
      risk_flags: result.risk_flags || [],
      score_details:
        asRecord(result.score_details) || asRecord(aggregateResult?.score_details) || undefined,
      completed_at: result.completed_at || asString(aggregateResult?.completed_at) || "",
    };
  });
}

export function buildEncounterConsultationSession(
  encounter: EncounterDetailData | null,
): ConsultationSession | null {
  const consultation = encounter?.consultation;
  if (!encounter || !consultation) {
    return null;
  }

  return {
    session_id: consultation.id,
    encounter_session_id: encounter.id,
    user_id: "",
    status: consultation.status,
    assigned_doctor_persona: consultation.assigned_doctor_persona || undefined,
    slot_values: consultation.slot_values || {},
    chief_complaint_summary: consultation.chief_complaint_summary,
    chief_complaint_structured_result:
      consultation.chief_complaint_structured_result || {},
    chief_complaint_stage_summary:
      consultation.chief_complaint_stage_summary || consultation.chief_complaint_summary || "",
    current_history_structured_result:
      consultation.current_history_structured_result || {},
    symptom_screening_stage_summary:
      consultation.symptom_screening_stage_summary || "",
    high_risk_screening_result: consultation.high_risk_screening_result || {},
    high_risk_screening_stage_summary:
      consultation.high_risk_screening_stage_summary || "",
    digital_human_consultation_summary:
      consultation.digital_human_consultation_summary || "",
    scale_handoff_payload: consultation.scale_handoff_payload || {},
    required_scales: consultation.required_scales || [],
    subtitle_history: (consultation.subtitle_history || []) as ConsultationSubtitleHistoryEntry[],
    created_at: consultation.created_at || undefined,
    started_at: consultation.started_at,
    completed_at: consultation.completed_at,
  };
}

export function buildEncounterAssessmentSession(
  encounter: EncounterDetailData | null,
): AssessmentSession | null {
  const assessment = encounter?.assessment;
  if (!encounter || !assessment) {
    return null;
  }

  const aggregatePayload = asRecord(assessment.aggregate_payload) || {};
  const scaleHandoffPayload = resolveAssessmentScaleHandoffPayload(
    assessment,
    encounter.consultation,
  );
  const assessmentResults = buildAssessmentResults(
    encounter.assessment_results,
    aggregatePayload,
  );
  const fallbackScaleSlugs = assessmentResults.map((item) => item.scale_slug);
  const requiredScales = assessment.required_scales?.length
    ? assessment.required_scales
    : asStringArray(scaleHandoffPayload.required_scales);
  const selectedScales = assessment.selected_scales?.length
    ? assessment.selected_scales
    : fallbackScaleSlugs.length
      ? fallbackScaleSlugs
      : requiredScales;

  return {
    session_id: assessment.id,
    user_id: "",
    encounter_session_id: encounter.id,
    source_consultation_flow_run_id: assessment.source_consultation_flow_run_id || undefined,
    multimodal_session_id: assessment.multimodal_session_id || undefined,
    status: assessment.status,
    required_scales: requiredScales,
    selected_scales: dedupeScaleSlugs(selectedScales),
    current_item_index: 0,
    scale_handoff_payload: scaleHandoffPayload,
    aggregate_payload: aggregatePayload,
    results: assessmentResults,
    created_at: assessment.created_at || undefined,
  };
}

export function buildHistoryInsightItems(
  record: Record<string, unknown> | null | undefined,
): HistoryInsightItem[] {
  if (!record) {
    return [];
  }

  return Object.entries(record).reduce<HistoryInsightItem[]>((accumulator, [key, value]) => {
    const normalized = formatInsightValue(value);
    if (!normalized) {
      return accumulator;
    }

    accumulator.push({
      label: formatInsightLabel(key),
      value: normalized,
    });
    return accumulator;
  }, []);
}

export function buildTranscriptPreview(
  entries: ConsultationSubtitleHistoryEntry[] | null | undefined,
  limit?: number,
) {
  const filtered = (entries || []).filter((entry) => entry?.text?.trim());
  return limit ? filtered.slice(-limit) : filtered;
}

const STAGE_LABELS: Record<string, string> = {
  "stage-01-greeting-and-briefing": "问候说明",
  "stage-02-chief-complaint": "主诉采集",
  "stage-03-symptom-screening": "症状筛查",
  "stage-04-high-risk-screening": "风险筛查",
  "handoff-to-scale-assessment": "量表说明",
};

/** 纯独白阶段：连续医生消息合并为一条 */
const MONOLOGUE_STAGES = new Set([
  "stage-01-greeting-and-briefing",
  "handoff-to-scale-assessment",
]);

export type TranscriptEntry = {
  speaker: "doctor" | "user";
  text: string;
  /** 来源：consultation / assessment */
  source: string;
};

export type TranscriptStageGroup = {
  stageId: string;
  stageLabel: string;
  /** section: "consultation" | "assessment" */
  section: string;
  entries: TranscriptEntry[];
};

/**
 * 将原始对话条目按阶段分组，并合并消息：
 * - 独白阶段（问候/量表说明）：连续医生消息合并为一条
 * - 问答阶段（主诉/症状/风险）：医生提问 + 用户回答 合并为一条
 */
function buildConsultationTranscriptGroups(
  entries: ConsultationSubtitleHistoryEntry[] | null | undefined,
): TranscriptStageGroup[] {
  const filtered = (entries || []).filter((e) => e?.text?.trim());
  if (!filtered.length) return [];

  // 按 stage_id 分桶
  const bucketMap = new Map<string, ConsultationSubtitleHistoryEntry[]>();
  const stageOrder: string[] = [];

  for (const entry of filtered) {
    const key = entry.stage_id || "__ungrouped";
    if (!bucketMap.has(key)) {
      stageOrder.push(key);
      bucketMap.set(key, []);
    }
    bucketMap.get(key)!.push(entry);
  }

  return stageOrder.map((stageId) => {
    const rawEntries = bucketMap.get(stageId)!;
    const isMonologue = MONOLOGUE_STAGES.has(stageId);
    const merged: TranscriptEntry[] = [];

    if (isMonologue) {
      // 独白阶段：合并所有连续医生消息为一条
      const doctorTexts = rawEntries
        .filter((e) => e.speaker === "doctor" && e.text?.trim())
        .map((e) => e.text.trim());
      if (doctorTexts.length) {
        merged.push({ speaker: "doctor", text: doctorTexts.join("\n"), source: "consultation" });
      }
      // 如果有用户消息也单独保留
      for (const e of rawEntries) {
        if (e.speaker === "user" && e.text?.trim()) {
          merged.push({ speaker: "user", text: e.text.trim(), source: "consultation" });
        }
      }
    } else {
      // 问答阶段：连续医生消息合并，然后与用户回答配对
      let pendingDoctor: string | null = null;
      for (const e of rawEntries) {
        const text = e.text?.trim();
        if (!text) continue;
        if (e.speaker === "doctor") {
          // 连续医生消息合并为一个问题
          pendingDoctor = pendingDoctor !== null ? `${pendingDoctor} ${text}` : text;
        } else if (e.speaker === "user") {
          if (pendingDoctor !== null) {
            // 配对：合并后的医生问题 + 用户回答
            merged.push({ speaker: "doctor", text: pendingDoctor, source: "consultation" });
            merged.push({ speaker: "user", text, source: "consultation" });
            pendingDoctor = null;
          } else {
            merged.push({ speaker: "user", text, source: "consultation" });
          }
        }
      }
      // 遗留的未配对医生消息
      if (pendingDoctor !== null) {
        merged.push({ speaker: "doctor", text: pendingDoctor, source: "consultation" });
      }
    }

    return {
      stageId,
      stageLabel: STAGE_LABELS[stageId] || stageId,
      section: "consultation",
      entries: merged,
    };
  });
}

function buildAssessmentTranscriptGroups(
  scaleDetails: Record<string, AssessmentScaleDetail> | null | undefined,
  orderedScaleSlugs?: string[] | null,
): TranscriptStageGroup[] {
  if (!scaleDetails) return [];
  const groups: TranscriptStageGroup[] = [];
  const scaleOrder = orderedScaleSlugs?.length
    ? dedupeScaleSlugs([...orderedScaleSlugs, ...Object.keys(scaleDetails)])
    : Object.keys(scaleDetails);

  for (const slug of scaleOrder) {
    const detail = scaleDetails[slug];
    if (!detail) continue;
    if (!detail.items?.length) continue;

    const entries: TranscriptEntry[] = [];

    for (const item of detail.items) {
      const question = item.question_text?.trim();
      const answer = item.selected_option_label?.trim() || item.transcript_text?.trim();
      if (question) {
        entries.push({ speaker: "doctor", text: question, source: "assessment" });
      }
      if (answer) {
        entries.push({ speaker: "user", text: answer, source: "assessment" });
      }
    }

    if (entries.length) {
      groups.push({
        stageId: `assessment:${slug}`,
        stageLabel: detail.scale_short_name || detail.scale_name || slug,
        section: "assessment",
        entries,
      });
    }
  }

  return groups;
}

/**
 * 构建完整对话分组：咨询阶段 + 量表阶段
 */
export function buildFullTranscriptGroups(
  consultationEntries: ConsultationSubtitleHistoryEntry[] | null | undefined,
  scaleDetails: Record<string, AssessmentScaleDetail> | null | undefined,
  orderedScaleSlugs?: string[] | null,
): TranscriptStageGroup[] {
  return [
    ...buildConsultationTranscriptGroups(consultationEntries),
    ...buildAssessmentTranscriptGroups(scaleDetails, orderedScaleSlugs),
  ];
}

export function getEncounterRiskSummary(
  encounter: EncounterDetailData | null,
): Record<string, unknown> | null {
  return asRecord(encounter?.assessment?.aggregate_payload?.risk_summary);
}

export function getEncounterRiskFrontDisplay(
  encounter: EncounterDetailData | null,
): Record<string, unknown> | null {
  return asRecord(getEncounterRiskSummary(encounter)?.front_display);
}
