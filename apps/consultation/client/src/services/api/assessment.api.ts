import { apiRequest, buildApiUrl } from "./client";
import type {
  AssessmentCatalogResponse,
  AssessmentScaleDetailResponse,
  AssessmentMultimodalLiveResponse,
  AssessmentSessionResponse,
  ConsultationTurnMultimodalBundleResponse,
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

export async function getAssessmentScaleDetail(sessionId: string, scaleSlug: string) {
  const data = await apiRequest<AssessmentScaleDetailResponse>(
    `/assessment/sessions/${sessionId}/scales/${scaleSlug}/detail`,
    {
      method: "GET",
    },
  );
  return data.scale_detail;
}

export async function getAssessmentMultimodalLive(sessionId: string) {
  const data = await apiRequest<AssessmentMultimodalLiveResponse>(
    `/assessment/sessions/${sessionId}/multimodal/live`,
    {
      method: "GET",
    },
  );
  return data;
}

export async function submitAssessmentAnswer(sessionId: string, payload: SubmitAssessmentAnswerPayload) {
  const data = await apiRequest<AssessmentSessionResponse>(`/assessment/sessions/${sessionId}/answers`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return data;
}

export function getAssessmentMultimodalLiveStreamUrl(sessionId: string) {
  return buildApiUrl(`/assessment/sessions/${sessionId}/multimodal/live/stream`);
}

export async function getAssessmentTurnMultimodalBundle(sessionId: string, turnId: string) {
  return apiRequest<ConsultationTurnMultimodalBundleResponse>(
    `/assessment/sessions/${sessionId}/turns/${turnId}/multimodal/bundle`,
    {
      method: "GET",
    },
  );
}
