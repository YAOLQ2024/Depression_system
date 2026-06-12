import type {
  EncounterAssessmentDetail,
  EncounterAssessmentResult,
  EncounterConsultationDetail,
  EncounterDetailData,
} from "../../services/api/contracts";
import type {
  AssessmentResult,
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

function formatInsightLabel(key: string) {
  return key.replace(/[_-]+/g, " ").trim() || key;
}

function formatInsightValue(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "string") {
    const normalized = value.trim();
    return normalized || null;
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
    : requiredScales.length
      ? requiredScales
      : fallbackScaleSlugs;

  return {
    session_id: assessment.id,
    user_id: "",
    encounter_session_id: encounter.id,
    source_consultation_flow_run_id: assessment.source_consultation_flow_run_id || undefined,
    multimodal_session_id: assessment.multimodal_session_id || undefined,
    status: assessment.status,
    required_scales: requiredScales,
    selected_scales: selectedScales,
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
  limit = 10,
) {
  const finalEntries = (entries || []).filter((entry) => entry?.text?.trim()).slice(-limit);
  return finalEntries;
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
