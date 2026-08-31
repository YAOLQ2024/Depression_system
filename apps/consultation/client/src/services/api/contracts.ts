import type {
  AssessmentCatalogItem,
  AssessmentScaleDetail,
  AssessmentSession,
  BootstrapPayload,
  ConsultationMultimodalLive,
  ConsultationSession,
  ConsultationSubtitleHistoryEntry,
  ConsultationTurnMultimodalBundle,
  UserRecord,
  VisualPipelineStatus,
} from "../../types";

export type AuthLoginRequest = {
  account: string;
  password: string;
};

export type AuthLoginResponse = {
  user: UserRecord;
  session_token?: string;
};

export type AuthRegisterRequest = {
  full_name: string;
  account: string;
  password: string;
};

export type UserResponse = {
  user: UserRecord;
};

export type PreparationStateResponse = {
  preparation_state: Record<string, unknown>;
  user?: UserRecord;
};

export type UpdateUserProfilePayload = {
  full_name?: string;
  age?: number;
  gender?: string;
  height_cm?: number;
  weight_kg?: number;
  marital_status?: string;
  parents_marital_status?: string;
  parents_occupation?: string;
  prior_psychiatric_visit?: string;
};

export type UpdateUserPreparationStatePayload = {
  device_status?: Record<string, unknown>;
  consent_confirmed?: boolean;
  consent_confirmed_at?: string | null;
  assigned_doctor_persona?: string | null;
  doctor_selected_at?: string | null;
};

export type AssessmentCatalogResponse = {
  catalog: AssessmentCatalogItem[];
};

export type ConsultationResponse = {
  consultation: ConsultationSession;
};

export type CreateConsultationSessionPayload = {
  device_status?: Record<string, unknown>;
  audio_channel_ready?: boolean;
  consent_confirmed?: boolean;
  consultation_ready_state?: string;
  assigned_doctor_persona?: string | null;
};

export type SubmitConsultationTurnPayload = {
  input_type: string;
  turn_id?: string | null;
  raw_input?: string | null;
  audio_uri?: string | null;
  transcript_text?: string | null;
  transcript_source?:
    | "dolphin_final"
    | "manual_input"
    | "continue_button"
    | "silence"
    | "recognition_failure"
    | null;
  response_started_at?: string | null;
  response_completed_at?: string | null;
  [key: string]: unknown;
};

export type ConsultationMultimodalCapturePayload = {
  question_key: string;
  turn_id?: string | null;
  sample_started_at: string;
  sample_ended_at: string;
  sample_index: number;
  mime_type: string;
  image_file: File;
};

export type ConsultationFrameCaptureResponse = {
  capture_id?: string | null;
  session_id?: string | null;
  question_key?: string | null;
  modality?: string | null;
  processing_status?: string | null;
  primary_label?: string | null;
  primary_score?: number | null;
  top_3_labels?: { label: string; score: number }[];
  quality_flags?: Record<string, number | boolean | null>;
  sample_started_at?: string | null;
  sample_ended_at?: string | null;
  sample_count?: number | null;
  valid_sample_count?: number | null;
  storage_uri?: string | null;
  error_message?: string | null;
  turn_bundle?: ConsultationTurnMultimodalBundle | null;
};

export type ConsultationVisualCaptureResponse = {
  visual_frame?: {
    visual_frame_id?: string | null;
    session_id?: string | null;
    turn_id?: string | null;
    question_key?: string | null;
    sample_index?: number | null;
    sample_started_at?: string | null;
    sample_ended_at?: string | null;
    storage_uri?: string | null;
    created_at?: string | null;
  } | null;
  face_result?: ConsultationFrameCaptureResponse | null;
  pose_result?: ConsultationFrameCaptureResponse | null;
  turn_bundle?: ConsultationTurnMultimodalBundle | null;
  visual_pipeline?: VisualPipelineStatus | null;
  multimodal_session?: Record<string, unknown> | null;
};

export type ConsultationMultimodalLiveResponse = ConsultationMultimodalLive;

export type ConsultationTurnMultimodalBundleResponse = ConsultationTurnMultimodalBundle;

export type AssessmentSessionResponse = {
  assessment_session: AssessmentSession;
  accepted_answer?: AssessmentAcceptedAnswer | null;
};

export type InterventionSession = {
  session_id: string;
  user_id: string;
  encounter_session_id?: string | null;
  consultation_session_id?: string | null;
  assessment_session_id?: string | null;
  plan_id?: string | null;
  risk_evaluation_id?: string | null;
  source: string;
  status: string;
  current_program_id?: string | null;
  current_program_title?: string | null;
  current_delivery_mode?: string | null;
  metadata?: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
  started_at?: string | null;
  last_event_at?: string | null;
  completed_at?: string | null;
};

export type InterventionEventRecord = {
  event_id: string;
  session_id: string;
  user_id: string;
  event_type: string;
  program_id?: string | null;
  program_title?: string | null;
  delivery_mode?: string | null;
  payload?: Record<string, unknown>;
  created_at?: string | null;
};

export type InterventionSessionResponse = {
  intervention_session: InterventionSession;
};

export type InterventionEventResponse = {
  session: InterventionSession;
  event: InterventionEventRecord;
};

export type CreateInterventionSessionPayload = {
  encounter_session_id?: string | null;
  consultation_session_id?: string | null;
  assessment_session_id?: string | null;
  plan_id?: string | null;
  risk_evaluation_id?: string | null;
  source?: string | null;
  metadata?: Record<string, unknown>;
};

export type RecordInterventionEventPayload = {
  event_type: string;
  program_id?: string | null;
  program_title?: string | null;
  delivery_mode?: string | null;
  payload?: Record<string, unknown>;
};

export type AssessmentScaleDetailResponse = {
  scale_detail: AssessmentScaleDetail;
};

export type AssessmentAcceptedAnswer = {
  answer_id: string;
  session_id: string;
  scale_slug: string;
  item_id: string;
  item_index: number;
  question_key?: string | null;
  turn_id?: string | null;
  answer_source?: string | null;
  selected_option_label?: string | null;
  selected_option_score?: number | null;
  transcript_text?: string | null;
  transcript_source?: string | null;
  audio_uri?: string | null;
  original_audio_uri?: string | null;
  normalized_wav_uri?: string | null;
  response_started_at?: string | null;
  response_completed_at?: string | null;
  capture_timestamp?: string | null;
  normalization_source?: string | null;
  created_at?: string | null;
};

export type AssessmentMultimodalLiveResponse = ConsultationMultimodalLive;

export type CreateAssessmentSessionPayload = {
  encounter_session_id?: string | null;
  source_consultation_flow_run_id?: string | null;
  multimodal_session_id?: string | null;
  scale_handoff_payload?: Record<string, unknown>;
  selected_scales?: string[];
  required_scales?: string[];
};

export type SubmitAssessmentAnswerPayload = {
  item_id?: string | null;
  selected_option_score?: number | null;
  selected_option_label?: string | null;
  question_key?: string | null;
  turn_id?: string | null;
  answer_source?: string | null;
  raw_input?: string | null;
  transcript_text?: string | null;
  transcript_source?:
    | "dolphin_final"
    | "manual_input"
    | "click_selection"
    | "recognition_failure"
    | null;
  audio_uri?: string | null;
  original_audio_uri?: string | null;
  normalized_wav_uri?: string | null;
  multimodal_session_id?: string | null;
  response_started_at?: string | null;
  response_completed_at?: string | null;
  capture_timestamp?: string | null;
};

export type BootstrapResponse = BootstrapPayload;

/** 单条就诊摘要（列表用） */
export type EncounterSummary = {
  id: string;
  status: string;
  current_flow_type: string;
  created_at: string | null;
  completed_at: string | null;
  consultation_session_id: string | null;
  assessment_session_id: string | null;
  chief_complaint_summary: string | null;
  phq9_score: number | null;
  phq9_risk_level: string | null;
  overall_risk_level: string | null;
};

/** 就诊列表 API 响应 */
export type EncounterListResponse = {
  encounters: EncounterSummary[];
  next_cursor: string | null;
  has_more: boolean;
};

/** 就诊时间线事件 */
export type EncounterTimelineEvent = {
  event: string;
  at: string | null;
};

/** 问诊摘要（详情用） */
export type EncounterConsultationDetail = {
  id: string;
  status: string;
  chief_complaint_raw_text?: string | null;
  chief_complaint_summary: string | null;
  assigned_doctor_persona: string | null;
  slot_values?: Record<string, unknown>;
  chief_complaint_structured_result?: Record<string, unknown>;
  chief_complaint_stage_summary?: string | null;
  current_history_structured_result?: Record<string, unknown>;
  symptom_screening_stage_summary?: string | null;
  high_risk_screening_result?: Record<string, unknown>;
  high_risk_screening_stage_summary?: string | null;
  digital_human_consultation_summary?: string | null;
  scale_handoff_payload?: Record<string, unknown>;
  required_scales?: string[];
  subtitle_history?: ConsultationSubtitleHistoryEntry[];
  context_snapshot?: Record<string, unknown>;
  created_at: string | null;
  completed_at: string | null;
  started_at: string | null;
};

/** 评估摘要（详情用） */
export type EncounterAssessmentDetail = {
  id: string;
  status: string;
  created_at: string | null;
  completed_at: string | null;
  aggregate_payload: Record<string, unknown> | null;
  scale_handoff_payload?: Record<string, unknown> | null;
  required_scales?: string[];
  selected_scales?: string[];
  source_consultation_flow_run_id?: string | null;
  multimodal_session_id?: string | null;
};

/** 评估结果条目 */
export type EncounterAssessmentResult = {
  scale_slug: string;
  raw_score: number;
  derived_score: number;
  normalized_score?: number | null;
  interpretation_level: string | null;
  interpretation_label: string | null;
  score_details?: Record<string, unknown> | null;
  risk_flags: Array<Record<string, unknown>>;
  completed_at: string | null;
};

/** 就诊详情 */
export type EncounterDetailData = {
  id: string;
  status: string;
  current_flow_type: string;
  created_at: string | null;
  completed_at: string | null;
  started_at: string | null;
  consultation: EncounterConsultationDetail | null;
  assessment: EncounterAssessmentDetail | null;
  assessment_results: EncounterAssessmentResult[];
  timeline: EncounterTimelineEvent[];
};

/** 就诊详情 API 响应 */
export type EncounterDetailResponse = {
  encounter: EncounterDetailData;
};

export type EncounterScaleHistoryPoint = {
  encounter_id?: string | null;
  encounter_status?: string | null;
  assessment_session_id?: string | null;
  assessment_status?: string | null;
  completed_at: string;
  raw_score?: number | null;
  derived_score?: number | null;
  score: number;
};

export type EncounterScaleHistoryResponse = {
  scale_slug: string;
  history: EncounterScaleHistoryPoint[];
};
