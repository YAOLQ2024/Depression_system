import type {
  AssessmentCatalogItem,
  AssessmentScaleDetail,
  AssessmentSession,
  BootstrapPayload,
  ConsultationMultimodalLive,
  ConsultationSession,
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

export type AssessmentCatalogResponse = {
  catalog: AssessmentCatalogItem[];
};

export type ConsultationResponse = {
  consultation: ConsultationSession;
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

export type CreateAssessmentSessionPayload = {
  encounter_session_id?: string | null;
  source_consultation_flow_run_id?: string | null;
  multimodal_session_id?: string | null;
  scale_handoff_payload?: Record<string, unknown>;
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
