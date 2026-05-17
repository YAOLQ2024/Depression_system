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

export type UserRecord = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  profile_status: string;
  profile?: UserPreparationProfile | null;
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

export type ConsultationSession = {
  session_id: string;
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
  current_prompt_key?: string | null;
  current_prompt_order?: number | null;
  current_prompt_video_asset_id?: string | null;
  current_prompt_video_uri?: string | null;
  current_prompt_question_text?: string | null;
  current_prompt_subtitle_text?: string | null;
  current_stage?: ConsultationStageProgress | null;
  status: string;
  assigned_doctor_persona?: string | null;
  requires_human_review?: boolean;
  current_prompt?: string | null;
  current_question_item?: ConsultationQuestionItem | null;
  participant_profile_snapshot?: Record<string, unknown>;
  slot_values?: Record<string, unknown>;
  chief_complaint_summary?: string | null;
  current_history_structured_result?: Record<string, unknown>;
  high_risk_screening_result?: Record<string, unknown>;
  scale_handoff_payload?: Record<string, unknown>;
  required_scales?: string[];
  created_at?: string;
  updated_at?: string;
  started_at?: string | null;
  completed_at?: string | null;
};

export type AssessmentOption = {
  score: number;
  label: string;
};

export type AssessmentCatalogItem = {
  slug: string;
  code: string;
  name: string;
  short_name: string;
  mode: string;
  timeframe?: string | null;
  item_count: number;
  answer_options: AssessmentOption[];
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
  interpretation_level?: string | null;
  interpretation_label?: string | null;
  risk_flags?: Array<Record<string, unknown>>;
  completed_at: string;
};

export type AssessmentSession = {
  session_id: string;
  user_id: string;
  consultation_session_id?: string | null;
  status: string;
  required_scales: string[];
  selected_scales: string[];
  current_scale_slug?: string | null;
  current_item_index: number;
  current_item?: AssessmentItem | null;
  scale_handoff_payload?: Record<string, unknown>;
  capture_context?: Record<string, unknown>;
  aggregate_payload?: Record<string, unknown>;
  results: AssessmentResult[];
  created_at?: string;
  updated_at?: string;
};
