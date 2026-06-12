import { apiRequest, buildApiUrl } from "./client";
import type {
  CreateConsultationSessionPayload,
  ConsultationMultimodalCapturePayload,
  ConsultationFrameCaptureResponse,
  ConsultationMultimodalLiveResponse,
  ConsultationResponse,
  ConsultationTurnMultimodalBundleResponse,
  ConsultationVisualCaptureResponse,
  SubmitConsultationTurnPayload,
} from "./contracts";
import type { EncounterListResponse, EncounterDetailResponse } from "./contracts";

export async function createConsultationSession(payload: CreateConsultationSessionPayload = {}) {
  const data = await apiRequest<ConsultationResponse>("/consultations", {
    method: "POST",
    body: JSON.stringify(payload),
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

export async function previewConsultationQuestionItemCompletion(sessionId: string, questionKey: string) {
  const data = await apiRequest<ConsultationResponse>(
    `/consultations/${sessionId}/question-items/${questionKey}/preview-complete`,
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

export function getConsultationMultimodalLiveStreamUrl(sessionId: string) {
  return buildApiUrl(`/consultations/${sessionId}/multimodal/live/stream`);
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
  formData.append("sample_started_at", payload.sample_started_at);
  formData.append("sample_ended_at", payload.sample_ended_at);
  formData.append("sample_index", String(payload.sample_index));
  formData.append("mime_type", payload.mime_type);
  formData.append("image_file", payload.image_file);
  return formData;
}

export async function submitConsultationVisualCapture(sessionId: string, payload: ConsultationMultimodalCapturePayload) {
  return apiRequest<ConsultationVisualCaptureResponse>(`/consultations/${sessionId}/multimodal/visual-captures`, {
    method: "POST",
    body: buildCaptureFormData(payload),
  });
}

export async function listEncounters(
  cursor?: string | null,
  limit: number = 10,
): Promise<EncounterListResponse> {
  const params = new URLSearchParams();
  if (cursor) params.set("cursor", cursor);
  params.set("limit", String(limit));
  const qs = params.toString();
  return apiRequest<EncounterListResponse>(`/encounters?${qs}`);
}

export async function getEncounterDetail(encounterId: string): Promise<EncounterDetailResponse> {
  return apiRequest<EncounterDetailResponse>(`/encounters/${encounterId}`);
}

export async function downloadEncounterPdf(encounterId: string): Promise<void> {
  const token = (() => {
    try {
      return localStorage.getItem("mcs_session_token") || sessionStorage.getItem("mcs_session_token") || "";
    } catch {
      return "";
    }
  })();
  const url = buildApiUrl(`/encounters/${encounterId}/pdf`);
  const response = await fetch(url, {
    credentials: "include",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    throw new Error(`下载失败 (${response.status})`);
  }
  const blob = await response.blob();
  const downloadUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = `encounter-${encounterId}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(downloadUrl);
}
