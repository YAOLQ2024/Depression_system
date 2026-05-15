import { apiRequest } from "./client";
import type {
  AssessmentCatalogResponse,
  AssessmentSessionResponse,
  CreateAssessmentSessionPayload,
  SubmitAssessmentAnswerPayload,
} from "./contracts";

export async function getAssessmentCatalog() {
  const data = await apiRequest<AssessmentCatalogResponse>("/assessment/catalog", { method: "GET" });
  return data.catalog || [];
}

export async function createAssessmentSession(payload: CreateAssessmentSessionPayload) {
  const data = await apiRequest<AssessmentSessionResponse>("/assessment/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return data.assessment_session;
}

export async function getAssessmentSession(sessionId: string) {
  const data = await apiRequest<AssessmentSessionResponse>(`/assessment/sessions/${sessionId}`, {
    method: "GET",
  });
  return data.assessment_session;
}

export async function submitAssessmentAnswer(sessionId: string, payload: SubmitAssessmentAnswerPayload) {
  const data = await apiRequest<AssessmentSessionResponse>(`/assessment/sessions/${sessionId}/answers`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return data.assessment_session;
}
