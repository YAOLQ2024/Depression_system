import { apiRequest } from "./client";
import type {
  EegClass,
  EegExplanation,
  EegHistoryPage,
  EegWindowRecord,
} from "../../components/eeg/eegMirrorTypes";

const base = (sessionId: string) =>
  `/multimodal/sessions/${encodeURIComponent(sessionId)}/eeg`;
export function getEegWindows(sessionId: string, signal?: AbortSignal) {
  return apiRequest<{ items: EegWindowRecord[]; next_cursor: string | null }>(
    `${base(sessionId)}/windows?limit=20`,
    { signal },
  );
}
export function getEegExplanationHistory(
  sessionId: string,
  target: EegClass,
  cursor: string | null,
  signal?: AbortSignal,
) {
  const query = new URLSearchParams({
    target_class: String(target),
    limit: "20",
  });
  if (cursor) query.set("cursor", cursor);
  return apiRequest<EegHistoryPage>(
    `${base(sessionId)}/explanations?${query}`,
    { signal },
  );
}
export function requestEegExplanation(
  sessionId: string,
  inferenceId: string,
  target: EegClass,
  signal?: AbortSignal,
) {
  return apiRequest<EegExplanation>(`${base(sessionId)}/explanations`, {
    method: "POST",
    body: JSON.stringify({ inference_id: inferenceId, target_class: target }),
    signal,
  });
}
export function getEegExplanation(
  sessionId: string,
  explanationId: string,
  signal?: AbortSignal,
) {
  return apiRequest<EegExplanation>(
    `${base(sessionId)}/explanations/${encodeURIComponent(explanationId)}`,
    { signal },
  );
}
