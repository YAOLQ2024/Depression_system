export type InterventionEntrySource =
  | "workflow_result"
  | "home_direct"
  | "sidebar_direct"
  | "standalone";

export type InterventionRouteState = {
  interventionSessionId?: string | null;
  encounterSessionId?: string | null;
  consultationSessionId?: string | null;
  assessmentSessionId?: string | null;
  bindConsultation?: boolean;
  source?: InterventionEntrySource;
};

export function normalizeInterventionRouteState(state: unknown): InterventionRouteState {
  if (!state || typeof state !== "object") {
    return {};
  }

  const candidate = state as Record<string, unknown>;
  return {
    interventionSessionId:
      typeof candidate.interventionSessionId === "string" ? candidate.interventionSessionId : null,
    encounterSessionId:
      typeof candidate.encounterSessionId === "string" ? candidate.encounterSessionId : null,
    consultationSessionId:
      typeof candidate.consultationSessionId === "string" ? candidate.consultationSessionId : null,
    assessmentSessionId:
      typeof candidate.assessmentSessionId === "string" ? candidate.assessmentSessionId : null,
    bindConsultation: Boolean(candidate.bindConsultation),
    source:
      candidate.source === "workflow_result" ||
      candidate.source === "home_direct" ||
      candidate.source === "sidebar_direct" ||
      candidate.source === "standalone"
        ? candidate.source
        : undefined,
  };
}

export function buildInterventionRouteState(
  baseState: InterventionRouteState,
  overrides: Partial<InterventionRouteState> = {},
): InterventionRouteState {
  return {
    ...baseState,
    ...overrides,
  };
}
