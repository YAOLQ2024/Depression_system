export type UserRecord = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  profile_status: string;
  profile?: Record<string, unknown>;
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

export type ConsultationSession = {
  session_id: string;
  user_id: string;
  workflow_stage_id?: string | null;
  current_stage_id?: string | null;
  current_node_id?: string | null;
  status: string;
  assigned_doctor_persona?: string | null;
  current_prompt?: string | null;
  chief_complaint_summary?: string | null;
  current_history_structured_result?: Record<string, unknown>;
  high_risk_screening_result?: Record<string, unknown>;
  scale_handoff_payload?: Record<string, unknown>;
  required_scales?: string[];
  created_at?: string;
  updated_at?: string;
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
