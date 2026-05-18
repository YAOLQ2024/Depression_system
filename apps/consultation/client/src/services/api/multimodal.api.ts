import { apiRequest } from "./client";

type MultimodalSessionResponse = {
  multimodal_session: {
    session_id: string;
    consultation_session_id: string;
    workflow_id?: string | null;
    status: string;
  };
};

type MultimodalAudioTurnResponse = {
  audio_turn: {
    audio_turn_id: string;
    multimodal_session_id: string;
    audio_uri: string;
    processing_status: string;
    stored_relative_path: string;
  };
};

export async function createMultimodalSession(payload: {
  consultation_session_id: string;
  workflow_id?: string | null;
}) {
  const data = await apiRequest<MultimodalSessionResponse>("/multimodal/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return data.multimodal_session;
}

export async function uploadMultimodalAudioTurn(
  sessionId: string,
  payload: {
    consultation_session_id: string;
    question_key: string;
    prompt_key?: string | null;
    duration_ms?: number | null;
    response_started_at?: string | null;
    response_completed_at?: string | null;
    audio_file: Blob;
    filename: string;
  },
) {
  const formData = new FormData();
  formData.set("consultation_session_id", payload.consultation_session_id);
  formData.set("question_key", payload.question_key);
  if (payload.prompt_key) {
    formData.set("prompt_key", payload.prompt_key);
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
