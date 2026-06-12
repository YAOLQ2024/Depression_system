import { useCallback, useEffect, useState } from "react";
import { getEncounterDetail } from "../services/api/consultation.api";
import type { EncounterDetailData } from "../services/api/contracts";

export type HistoryDetailState = {
  encounter: EncounterDetailData | null;
  loading: boolean;
  error: string | null;
};

export function useHistoryDetail(encounterId: string | undefined) {
  const [state, setState] = useState<HistoryDetailState>({
    encounter: null,
    loading: false,
    error: null,
  });

  const load = useCallback(async () => {
    if (!encounterId) return;
    setState({ encounter: null, loading: true, error: null });
    try {
      const result = await getEncounterDetail(encounterId);
      setState({ encounter: result.encounter, loading: false, error: null });
    } catch (err: any) {
      setState({
        encounter: null,
        loading: false,
        error: err?.message || "加载失败",
      });
    }
  }, [encounterId]);

  useEffect(() => {
    load();
  }, [load]);

  return { state, reload: load };
}
