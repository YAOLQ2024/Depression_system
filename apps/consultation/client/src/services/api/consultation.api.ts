import { apiRequest } from "./client";
import type {
  ConsultationMultimodalCapturePayload,
  ConsultationMultimodalLiveResponse,
  ConsultationResponse,
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
