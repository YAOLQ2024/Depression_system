import { useEffect, useEffectEvent, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  createInterventionSession,
  recordInterventionEvent,
} from "../../services/api/intervention.api";
import type { RecordInterventionEventPayload } from "../../services/api/contracts";
import {
  buildInterventionRouteState,
  normalizeInterventionRouteState,
  type InterventionRouteState,
} from "./sessionState";

type UseInterventionExecutionOptions = {
  pageTag: string;
  openEvent?: RecordInterventionEventPayload;
};

const DEFAULT_SOURCE = "standalone";

export function useInterventionExecution({ pageTag, openEvent }: UseInterventionExecutionOptions) {
  const location = useLocation();
  const navigate = useNavigate();
  const routeState = normalizeInterventionRouteState(location.state);
  const [interventionSessionId, setInterventionSessionId] = useState<string | null>(
    routeState.interventionSessionId ?? null,
  );
  const [sessionError, setSessionError] = useState("");
  const creationPromiseRef = useRef<Promise<string | null> | null>(null);
  const openEventTrackedRef = useRef(false);

  useEffect(() => {
    if (routeState.interventionSessionId && routeState.interventionSessionId !== interventionSessionId) {
      setInterventionSessionId(routeState.interventionSessionId);
    }
  }, [interventionSessionId, routeState.interventionSessionId]);

  const ensureSession = useEffectEvent(async () => {
    if (interventionSessionId) {
      return interventionSessionId;
    }

    if (creationPromiseRef.current) {
      return creationPromiseRef.current;
    }

    const shouldBindConsultation = Boolean(routeState.bindConsultation && routeState.consultationSessionId);
    const createPromise = (async () => {
      try {
        const session = await createInterventionSession({
          encounter_session_id: shouldBindConsultation ? routeState.encounterSessionId ?? null : null,
          consultation_session_id: shouldBindConsultation ? routeState.consultationSessionId ?? null : null,
          assessment_session_id: shouldBindConsultation ? routeState.assessmentSessionId ?? null : null,
          source: routeState.source ?? DEFAULT_SOURCE,
          metadata: {
            page_tag: pageTag,
            bind_consultation: shouldBindConsultation,
          },
        });
        setInterventionSessionId(session.session_id);
        setSessionError("");
        navigate(location.pathname, {
          replace: true,
          state: buildInterventionRouteState(routeState, {
            interventionSessionId: session.session_id,
          }),
        });
        return session.session_id;
      } catch (error) {
        setSessionError(error instanceof Error ? error.message : "干预会话创建失败");
        return null;
      } finally {
        creationPromiseRef.current = null;
      }
    })();

    creationPromiseRef.current = createPromise;
    return createPromise;
  });

  const trackEvent = useEffectEvent(async (payload: RecordInterventionEventPayload) => {
    const sessionId = await ensureSession();
    if (!sessionId) {
      return null;
    }

    try {
      await recordInterventionEvent(sessionId, payload);
      return sessionId;
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : "干预记录写入失败");
      return null;
    }
  });

  useEffect(() => {
    if (openEventTrackedRef.current) {
      return;
    }
    openEventTrackedRef.current = true;
    if (openEvent) {
      void trackEvent(openEvent);
      return;
    }
    void ensureSession();
  }, [ensureSession, openEvent, trackEvent]);

  const buildRouteState = useEffectEvent((overrides: Partial<InterventionRouteState> = {}) =>
    buildInterventionRouteState(routeState, {
      interventionSessionId,
      ...overrides,
    }),
  );

  return {
    interventionSessionId,
    routeState,
    sessionError,
    ensureSession,
    trackEvent,
    buildRouteState,
  };
}
