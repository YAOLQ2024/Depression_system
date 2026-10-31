export type UserPreparationProfile = {
  gender?: string | null;
  age?: number | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  marital_status?: string | null;
  parents_marital_status?: string | null;
  parents_occupation?: string | null;
  prior_psychiatric_visit?: string | null;
};

export type UserPreparationState = {
  device_status?: Record<string, unknown>;
  consent_confirmed?: boolean;
  consent_confirmed_at?: string | null;
  assigned_doctor_persona?: string | null;
  doctor_selected_at?: string | null;
  updated_at?: string | null;
};

export type UserRecord = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  profile_status: string;
  profile?: UserPreparationProfile | null;
  preparation_state?: UserPreparationState | null;
};

export type WorkflowStageSummary = {
  id: string;
  name: string;
};

export type DoctorPersona = {
  persona_id: string;
  display_name: string;
};

export type BootstrapPayload = {
  workflow?: {
    workflow_id?: string;
    title?: string;
    stages?: WorkflowStageSummary[];
  };
  doctor_personas?: DoctorPersona[];
};

export type ConsultationStageProgress = {
  stage_id: string;
  stage_label: string;
  stage_order: number;
  total_stages: number;
};

export type ConsultationQuestionItem = {
  question_key: string;
  stage_id: string;
  stage_label: string;
  stage_order: number;
  order: number;
  node_id: string;
  video_asset_id?: string | null;
  video_uri?: string | null;
  question_text?: string | null;
  subtitle_text?: string | null;
  response_required: boolean;
};

export type ConsultationTurnRecord = {
  turn_id: string;
  session_id: string;
  encounter_session_id?: string | null;
  consultation_flow_run_id?: string | null;
  stage_id?: string | null;
  node_id?: string | null;
  turn_index?: number | null;
  question_key?: string | null;
  question_order?: number | null;
  question_text?: string | null;
  question_subtitle_text?: string | null;
  input_type: string;
  raw_input?: string | null;
  audio_uri?: string | null;
  original_audio_uri?: string | null;
  normalized_wav_uri?: string | null;
  transcript_text?: string | null;
  transcript_source?: string | null;
  turn_summary_payload?: Record<string, unknown> | null;
  branch_taken?: string | null;
  turn_window_started_at?: string | null;
  turn_window_completed_at?: string | null;
  response_started_at?: string | null;
  response_completed_at?: string | null;
  created_at?: string;
};

export type ConsultationSubtitleHistoryEntry = {
  entry_key: string;
  speaker: "doctor" | "user";
  text: string;
  status: "draft" | "final" | string;
  source?: string | null;
  prompt_key?: string | null;
  stage_id?: string | null;
  node_id?: string | null;
  turn_id?: string | null;
  sequence: number;
  created_at?: string | null;
  updated_at?: string | null;
};

export type MultimodalRankedLabel = {
  label: string;
  score: number;
};

export type SpeechMultimodalLive = {
  status: string;
  primary_label?: string | null;
  primary_score?: number | null;
  top_3_labels?: MultimodalRankedLabel[];
  audio_uri?: string | null;
  captured_at?: string | null;
};

export type TextMultimodalLive = {
  status: string;
  primary_label?: string | null;
  primary_score?: number | null;
  top_3_labels?: MultimodalRankedLabel[];
  negative_terms?: string[];
  transcript_text?: string | null;
  captured_at?: string | null;
};

export type FacePoseQualityFlags = Record<string, number | boolean | null>;

export type FacePoseMultimodalLive = {
  status: string;
  processing_status?: string | null;
  primary_label?: string | null;
  primary_score?: number | null;
  top_3_labels?: MultimodalRankedLabel[];
  quality_flags?: FacePoseQualityFlags;
  latest_capture_at?: string | null;
  sample_count?: number | null;
  valid_sample_count?: number | null;
  error_message?: string | null;
};

export type EegWaveSample = {
  seq: number;
  captured_at?: string | null;
  values: number[];
};

export type EegLiveResult = {
  sample_id?: string | null;
  inference_id?: string | null;
  model_sha256?: string | null;
  score_kind?: string | null;
  window_index?: number | null;
  primary_label?: string | null;
  primary_score?: number | null;
  top_3_labels?: MultimodalRankedLabel[];
  feature_frame_count?: number | null;
  sample_started_at?: string | null;
  sample_ended_at?: string | null;
  raw_eeg_uri?: string | null;
  model_version?: string | null;
  quality_flags?: Record<string, number | boolean | null>;
};

export type EegLivePayload = {
  status: string;
  device_status?: string | null;
  device_id?: string | null;
  channel_names?: string[];
  sampling_rate?: number | null;
  updated_at?: string | null;
  turn_id?: string | null;
  model_name?: string | null;
  model_version?: string | null;
  latest_result?: EegLiveResult | null;
  latest_results?: EegLiveResult[];
  calibration?: {
    required: boolean;
    status: "not_required" | "pending" | "collecting" | "ready";
    collected_frames: number;
    target_frames: number;
  };
  error_message?: string | null;
};

export type EegWavePreview = {
  status: string;
  channel_names?: string[];
  sampling_rate?: number | null;
  samples?: EegWaveSample[];
  append_samples?: EegWaveSample[];
  reset?: boolean;
};

export type ConsultationMultimodalLive = {
  speech: SpeechMultimodalLive;
  text: TextMultimodalLive;
  face: FacePoseMultimodalLive;
  pose: FacePoseMultimodalLive;
  eeg_live: EegLivePayload;
  eeg_waves: EegWavePreview;
  eeg_explanation_status?: { explanation_id: string; sample_id: string; inference_id: string; target_class: number; status: string };
  updated_at?: string | null;
};

export type ConsultationMultimodalLivePatch = Partial<ConsultationMultimodalLive> & {
  session_id?: string;
  eeg_waves?: Partial<EegWavePreview>;
};

export type ConsultationTurnMultimodalBundle = {
  turn_id?: string | null;
  session_id?: string | null;
  flow_run_id?: string | null;
  origin_flow_type?: string | null;
  stage_id?: string | null;
  question_key?: string | null;
  generated_at?: string | null;
  speech_features?: Record<string, unknown>;
  text_features?: Record<string, unknown>;
  face_features?: Record<string, unknown>;
  pose_features?: Record<string, unknown>;
  updated_at?: string | null;
};

export type ConsultationSession = {
  session_id: string;
  encounter_session_id?: string | null;
  user_id: string;
  workflow_id?: string | null;
  script_bundle?: string | null;
  playlist_version?: string | null;
  playlist_manifest_status?: string | null;
  delivery_mode?: string | null;
  total_prompt_count?: number | null;
  completed_prompt_count?: number | null;
  workflow_stage_id?: string | null;
  current_stage_id?: string | null;
  current_node_id?: string | null;
  current_question_key?: string | null;
  current_question_order?: number | null;
  current_question_video_asset_id?: string | null;
  current_question_video_uri?: string | null;
  current_question_text?: string | null;
  current_question_subtitle_text?: string | null;
  current_stage?: ConsultationStageProgress | null;
  status: string;
  current_turn_id?: string | null;
  assigned_doctor_persona?: string | null;
  requires_human_review?: boolean;
  current_prompt?: string | null;
  current_question_item?: ConsultationQuestionItem | null;
  participant_profile_snapshot?: Record<string, unknown>;
  slot_values?: Record<string, unknown>;
  chief_complaint_summary?: string | null;
  chief_complaint_structured_result?: Record<string, unknown>;
  chief_complaint_stage_summary?: string | null;
  current_history_structured_result?: Record<string, unknown>;
  symptom_screening_stage_summary?: string | null;
  high_risk_screening_result?: Record<string, unknown>;
  high_risk_screening_stage_summary?: string | null;
  digital_human_consultation_summary?: string | null;
  scale_handoff_payload?: Record<string, unknown>;
  required_scales?: string[];
  multimodal_session_id?: string | null;
  multimodal_live?: ConsultationMultimodalLive;
  multimodal_live_updated_at?: string | null;
  current_turn_bundle?: ConsultationTurnMultimodalBundle | null;
  visual_pipeline?: VisualPipelineStatus | null;
  subtitle_history?: ConsultationSubtitleHistoryEntry[];
  created_at?: string;
  updated_at?: string;
  started_at?: string | null;
  completed_at?: string | null;
};

export type AssessmentOption = {
  score: number;
  label: string;
};

export type AssessmentCatalogScaleItem = {
  id: string;
  index: number;
  text: string;
  question_text?: string | null;
  video_uri?: string | null;
};

export type AssessmentCatalogItem = {
  slug: string;
  code: string;
  name: string;
  short_name: string;
  mode: string;
  timeframe?: string | null;
  item_count: number;
  stage_intro_text?: string | null;
  stage_intro_video_uri?: string | null;
  answer_options: AssessmentOption[];
  items: AssessmentCatalogScaleItem[];
};

export type VisualPipelineStatus = {
  state_store: "redis_hot" | "postgres_cold" | "persisted_only";
  live_state_source: "redis" | "postgres" | "snapshot";
  turn_bundle_source: "redis" | "postgres" | "database" | "snapshot";
  degraded: boolean;
  fallback_reason?: string | null;
};

export type AssessmentItem = {
  scale_slug: string;
  item_id: string;
  index: number;
  text: string;
  answer_options: AssessmentOption[];
};

export type AssessmentResult = {
  scale_slug: string;
  raw_score: number;
  derived_score: number;
  normalized_score?: number | null;
  interpretation_level?: string | null;
  interpretation_label?: string | null;
  risk_flags?: Array<Record<string, unknown>>;
  score_details?: Record<string, unknown>;
  completed_at: string;
};

export type AssessmentScaleDetailItem = {
  item_id: string;
  item_index: number;
  question_key?: string | null;
  question_text: string;
  selected_option_label?: string | null;
  selected_option_score?: number | null;
  answer_source?: string | null;
  transcript_text?: string | null;
  transcript_source?: string | null;
  response_started_at?: string | null;
  response_completed_at?: string | null;
  capture_timestamp?: string | null;
  answered_at?: string | null;
};

export type AssessmentScaleDetail = {
  session_id: string;
  scale_slug: string;
  scale_code: string;
  scale_name: string;
  scale_short_name: string;
  status: string;
  configured_item_count: number;
  answered_item_count: number;
  raw_score?: number | null;
  derived_score?: number | null;
  normalized_score?: number | null;
  interpretation_level?: string | null;
  interpretation_label?: string | null;
  risk_flags?: Array<Record<string, unknown>>;
  completed_at?: string | null;
  answer_options: AssessmentOption[];
  items: AssessmentScaleDetailItem[];
};

export type AssessmentSession = {
  session_id: string;
  user_id: string;
  encounter_session_id?: string | null;
  source_consultation_flow_run_id?: string | null;
  multimodal_session_id?: string | null;
  status: string;
  required_scales: string[];
  selected_scales: string[];
  current_scale_slug?: string | null;
  current_item_index: number;
  current_item?: AssessmentItem | null;
  current_turn_id?: string | null;
  scale_handoff_payload?: Record<string, unknown>;
  capture_context?: Record<string, unknown>;
  aggregate_payload?: Record<string, unknown>;
  multimodal_live?: ConsultationMultimodalLive;
  multimodal_live_updated_at?: string | null;
  results: AssessmentResult[];
  created_at?: string;
  updated_at?: string;
};
