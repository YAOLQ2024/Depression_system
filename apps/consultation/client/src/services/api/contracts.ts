import type {
  AssessmentCatalogItem,
  AssessmentSession,
  BootstrapPayload,
  ConsultationSession,
  UserRecord,
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
  raw_input?: string | null;
  audio_uri?: string | null;
  transcript_text?: string | null;
  response_started_at?: string | null;
  response_completed_at?: string | null;
  [key: string]: unknown;
};

export type AssessmentSessionResponse = {
  assessment_session: AssessmentSession;
};

export type CreateAssessmentSessionPayload = {
  consultation_session_id: string;
  scale_handoff_payload?: Record<string, unknown>;
};

export type SubmitAssessmentAnswerPayload = {
  item_id?: string | null;
  selected_option_score: number;
  raw_input?: string | null;
};

export type BootstrapResponse = BootstrapPayload;
