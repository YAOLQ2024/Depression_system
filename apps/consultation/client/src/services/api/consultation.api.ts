import { apiRequest } from "./client";
import type { ConsultationResponse, SubmitConsultationTurnPayload } from "./contracts";

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
