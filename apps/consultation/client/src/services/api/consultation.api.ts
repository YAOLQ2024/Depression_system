import { apiRequest } from "./client";
import type {
  ConsultationAudioTurnResponse,
  ConsultationMultimodalCapturePayload,
  ConsultationMultimodalLiveResponse,
  ConsultationSubtitlePreviewPayload,
  ConsultationResponse,
  ConsultationTurnDetailResponse,
  ConsultationTurnMultimodalBundleResponse,
  SubmitConsultationTurnPayload,
} from "./contracts";

export async function createConsultationSession() {
  const data = await apiRequest<ConsultationResponse>("/consultations", {
    method: "POST",
    body: JSON.stringify({}),
  });
  return data.consultation;
}

export async function getConsultationSession(sessionId: string) {
  const data = await apiRequest<ConsultationResponse>(`/consultations/${sessionId}`, {
    method: "GET",
  });
  return data.consultation;
}

export async function startConsultationSession(sessionId: string) {
  const data = await apiRequest<ConsultationResponse>(`/consultations/${sessionId}/start`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  return data.consultation;
}

export async function submitConsultationTurn(sessionId: string, payload: SubmitConsultationTurnPayload) {
  const data = await apiRequest<ConsultationResponse>(`/consultations/${sessionId}/turns`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return data.consultation;
}

export async function submitConsultationAudioTurn(
  sessionId: string,
  payload: {
    transcript_text?: string | null;
    response_started_at?: string | null;
    response_completed_at?: string | null;
    mime_type?: string | null;
    audio_file: Blob;
    filename: string;
  },
) {
  const formData = new FormData();
  if (payload.transcript_text) {
    formData.append("transcript_text", payload.transcript_text);
  }
  if (payload.response_started_at) {
    formData.append("response_started_at", payload.response_started_at);
  }
  if (payload.response_completed_at) {
    formData.append("response_completed_at", payload.response_completed_at);
  }
  if (payload.mime_type) {
    formData.append("mime_type", payload.mime_type);
  }
  formData.append("audio_file", payload.audio_file, payload.filename);

  return apiRequest<ConsultationAudioTurnResponse>(
    `/consultations/${sessionId}/turns/audio`,
    {
      method: "POST",
      body: formData,
    },
  );
}

export async function getConsultationTurnDetail(sessionId: string, turnId: string) {
  return apiRequest<ConsultationTurnDetailResponse>(
    `/consultations/${sessionId}/turns/${turnId}`,
    {
      method: "GET",
    },
  );
}

export async function syncConsultationSubtitlePreview(sessionId: string, payload: ConsultationSubtitlePreviewPayload) {
  const data = await apiRequest<ConsultationResponse>(`/consultations/${sessionId}/subtitle-preview`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return data.consultation;
}

export async function completeConsultationQuestionItem(sessionId: string, questionKey: string) {
  const data = await apiRequest<ConsultationResponse>(
    `/consultations/${sessionId}/question-items/${questionKey}/complete`,
    {
      method: "POST",
      body: JSON.stringify({}),
    },
  );
  return data.consultation;
}

export async function getConsultationMultimodalLive(sessionId: string) {
  return apiRequest<ConsultationMultimodalLiveResponse>(`/consultations/${sessionId}/multimodal/live`, {
    method: "GET",
  });
}

export async function getConsultationTurnMultimodalBundle(sessionId: string, turnId: string) {
  return apiRequest<ConsultationTurnMultimodalBundleResponse>(
    `/consultations/${sessionId}/turns/${turnId}/multimodal/bundle`,
    {
      method: "GET",
    },
  );
}

function buildCaptureFormData(payload: ConsultationMultimodalCapturePayload) {
  const formData = new FormData();
  formData.append("question_key", payload.question_key);
  if (payload.turn_id) {
    formData.append("turn_id", payload.turn_id);
  }
  formData.append("capture_started_at", payload.capture_started_at);
  formData.append("capture_ended_at", payload.capture_ended_at);
  formData.append("frame_index", String(payload.frame_index));
  formData.append("mime_type", payload.mime_type);
  formData.append("image_file", payload.image_file);
  return formData;
}

export async function submitConsultationFaceCapture(sessionId: string, payload: ConsultationMultimodalCapturePayload) {
  return apiRequest<Record<string, unknown>>(`/consultations/${sessionId}/multimodal/captures/face`, {
    method: "POST",
    body: buildCaptureFormData(payload),
  });
}

export async function submitConsultationPoseCapture(sessionId: string, payload: ConsultationMultimodalCapturePayload) {
  return apiRequest<Record<string, unknown>>(`/consultations/${sessionId}/multimodal/captures/pose`, {
    method: "POST",
    body: buildCaptureFormData(payload),
  });
}
