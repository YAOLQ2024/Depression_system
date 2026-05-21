import { apiRequest } from "./client";

export type MultimodalSessionRecord = {
  session_id: string;
  flow_type?: string | null;
  flow_run_id?: string | null;
  user_id?: string | null;
  stage_context: {
    stage_id: string;
    stage_label: string;
    stage_order: number;
  };
  status: string;
  started_at: string;
  updated_at: string;
};

export type MultimodalAudioTurnRecord = {
  audio_turn_id: string;
  session_id: string;
  flow_run_id?: string | null;
  question_key: string;
  processing_status:
    | "uploaded"
    | "transcribing"
    | "transcript_ready"
    | "analyzing"
    | "completed"
    | "failed";
  audio_uri: string | null;
  normalized_wav_uri?: string | null;
  transcript_text: string | null;
  transcript_confidence: number | null;
  asr_provider: string;
  error_code: string | null;
  error_message: string | null;
  response_started_at: string | null;
  response_completed_at: string | null;
  created_at: string;
  updated_at: string;
};

type MultimodalSessionResponse = {
  multimodal_session: MultimodalSessionRecord;
};

type MultimodalAudioTurnResponse = {
  audio_turn: MultimodalAudioTurnRecord;
};

export async function createMultimodalSession(payload: {
  flow_type: string;
  flow_run_id: string;
  encounter_session_id?: string | null;
  stage_context: {
    stage_id: string;
    stage_label: string;
    stage_order: number;
  };
}) {
  const data = await apiRequest<MultimodalSessionResponse>("/multimodal/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return data.multimodal_session;
}

export async function warmupMultimodalSession(
  sessionId: string,
  payload: { modalities?: string[] } = {},
) {
  const data = await apiRequest<MultimodalSessionResponse>(
    `/multimodal/sessions/${sessionId}/warmup`,
    {
      method: "POST",
      body: JSON.stringify({
        modalities: payload.modalities || ["text", "audio", "face", "pose"],
      }),
    },
  );
  return data.multimodal_session;
}

export async function uploadMultimodalAudioTurn(
  sessionId: string,
  payload: {
    flow_run_id: string;
    question_key: string;
    stage_id: string;
    node_id: string;
    duration_ms?: number | null;
    response_started_at?: string | null;
    response_completed_at?: string | null;
    mime_type: string;
    turn_id?: string | null;
    audio_file: Blob;
    filename: string;
  },
) {
  const formData = new FormData();
  formData.set("flow_run_id", payload.flow_run_id);
  formData.set("question_key", payload.question_key);
  formData.set("stage_id", payload.stage_id);
  formData.set("node_id", payload.node_id);
  formData.set("mime_type", payload.mime_type);
  if (payload.turn_id) {
    formData.set("turn_id", payload.turn_id);
  }
  if (typeof payload.duration_ms === "number") {
    formData.set("duration_ms", String(payload.duration_ms));
  }
  if (payload.response_started_at) {
    formData.set("response_started_at", payload.response_started_at);
  }
  if (payload.response_completed_at) {
    formData.set("response_completed_at", payload.response_completed_at);
  }
  formData.set("audio_file", payload.audio_file, payload.filename);

  const data = await apiRequest<MultimodalAudioTurnResponse>(
    `/multimodal/sessions/${sessionId}/audio-turns`,
    {
      method: "POST",
      body: formData,
    },
  );
  return data.audio_turn;
}

export async function getMultimodalAudioTurn(sessionId: string, audioTurnId: string) {
  const data = await apiRequest<MultimodalAudioTurnResponse>(
    `/multimodal/sessions/${sessionId}/audio-turns/${audioTurnId}`,
    {
      method: "GET",
    },
  );
  return data.audio_turn;
}
