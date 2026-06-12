import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { APP_PATHS } from "../routes";
import type { EncounterSummary } from "../services/api/contracts";

const STORAGE_PREFIX_CONSULTATION = "mcs_consultation_session:";
const STORAGE_PREFIX_ASSESSMENT = "mcs_assessment_session:";

function getStorage(): Storage {
  try {
    const test = "__mcs_test__";
    localStorage.setItem(test, "1");
    localStorage.removeItem(test);
    return localStorage;
  } catch {
    return sessionStorage;
  }
}

function getUserId(): string | null {
  try {
    const raw = localStorage.getItem("mcs_user") || sessionStorage.getItem("mcs_user");
    if (raw) {
      const parsed = JSON.parse(raw);
      return parsed?.id || null;
    }
  } catch {}
  return null;
}

export type ResumeDialogState = {
  open: boolean;
  encounter: EncounterSummary | null;
};

export function useResumeEncounter() {
  const navigate = useNavigate();
  const [dialog, setDialog] = useState<ResumeDialogState>({
    open: false,
    encounter: null,
  });

  const promptResume = useCallback((encounter: EncounterSummary) => {
    setDialog({ open: true, encounter });
  }, []);

  const cancelResume = useCallback(() => {
    setDialog({ open: false, encounter: null });
  }, []);

  const confirmResume = useCallback(() => {
    const encounter = dialog.encounter;
    if (!encounter) return;

    const userId = getUserId();
    if (!userId) {
      setDialog({ open: false, encounter: null });
      return;
    }

    const storage = getStorage();

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

    setDialog({ open: false, encounter: null });

    if (encounter.current_flow_type === "assessment" && encounter.assessment_session_id) {
      navigate(APP_PATHS.assessment);
    } else {
      navigate(APP_PATHS.consultation);
    }
  }, [dialog.encounter, navigate]);

  return { dialog, promptResume, cancelResume, confirmResume };
}
