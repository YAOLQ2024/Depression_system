import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { APP_PATHS } from "../routes";
import { getSessionPersistenceMode } from "../services/api/client";
import type { EncounterSummary } from "../services/api/contracts";

const STORAGE_PREFIX_CONSULTATION = "mcs_consultation_session:";
const STORAGE_PREFIX_ASSESSMENT = "mcs_assessment_session:";

function getPrimaryStorage(): Storage {
  try {
    return getSessionPersistenceMode() === "session" ? sessionStorage : localStorage;
  } catch {
    return sessionStorage;
  }
}

function clearPersistedSessionIds(userId: string) {
  const consultationKey = `${STORAGE_PREFIX_CONSULTATION}${userId}`;
  const assessmentKey = `${STORAGE_PREFIX_ASSESSMENT}${userId}`;
  window.localStorage.removeItem(consultationKey);
  window.localStorage.removeItem(assessmentKey);
  window.sessionStorage.removeItem(consultationKey);
  window.sessionStorage.removeItem(assessmentKey);
}

export type ResumeDialogState = {
  open: boolean;
  encounter: EncounterSummary | null;
};

export function useResumeEncounter() {
  const navigate = useNavigate();
  const { state, actions } = useConsultationAppContext();
  const [dialog, setDialog] = useState<ResumeDialogState>({
    open: false,
    encounter: null,
  });
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [isResuming, setIsResuming] = useState(false);

  const promptResume = useCallback((encounter: EncounterSummary) => {
    setResumeError(null);
    setDialog({ open: true, encounter });
  }, []);

  const cancelResume = useCallback(() => {
    if (isResuming) {
      return;
    }
    setResumeError(null);
    setDialog({ open: false, encounter: null });
  }, [isResuming]);

  const confirmResume = useCallback(async () => {
    const encounter = dialog.encounter;
    const userId = state.user?.id;
    if (!encounter || !userId || isResuming) {
      return;
    }

    setIsResuming(true);
    setResumeError(null);

    try {
      clearPersistedSessionIds(userId);

      const storage = getPrimaryStorage();

      if (encounter.consultation_session_id) {
        storage.setItem(
          `${STORAGE_PREFIX_CONSULTATION}${userId}`,
          encounter.consultation_session_id,
        );
      }
      if (encounter.assessment_session_id) {
        storage.setItem(
          `${STORAGE_PREFIX_ASSESSMENT}${userId}`,
          encounter.assessment_session_id,
        );
      }

      await actions.rehydrateFromStorage();

      setDialog({ open: false, encounter: null });
      navigate(
        encounter.current_flow_type === "assessment" && encounter.assessment_session_id
          ? APP_PATHS.assessment
          : APP_PATHS.consultation,
      );
    } catch (caught) {
      setResumeError(caught instanceof Error ? caught.message : "恢复会话失败，请稍后重试。");
    } finally {
      setIsResuming(false);
    }
  }, [actions, dialog.encounter, isResuming, navigate, state.user?.id]);

  return {
    dialog,
    promptResume,
    cancelResume,
    confirmResume,
    isResuming,
    resumeError,
  };
}
