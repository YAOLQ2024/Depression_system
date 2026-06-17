import { apiRequest } from "./client";
import type {
  CreateInterventionSessionPayload,
  InterventionEventResponse,
  InterventionSessionResponse,
  RecordInterventionEventPayload,
} from "./contracts";

export async function createInterventionSession(payload: CreateInterventionSessionPayload) {
  const data = await apiRequest<InterventionSessionResponse>("/interventions/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return data.intervention_session;
}

export async function getInterventionSession(sessionId: string) {
  const data = await apiRequest<InterventionSessionResponse>(`/interventions/sessions/${sessionId}`, {
    method: "GET",
  });
  return data.intervention_session;
}

export async function recordInterventionEvent(sessionId: string, payload: RecordInterventionEventPayload) {
  return apiRequest<InterventionEventResponse>(`/interventions/sessions/${sessionId}/events`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
