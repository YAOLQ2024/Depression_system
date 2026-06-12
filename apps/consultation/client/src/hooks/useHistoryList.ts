import { useCallback, useRef, useState } from "react";
import { listEncounters } from "../services/api/consultation.api";
import type { EncounterSummary } from "../services/api/contracts";

export type HistoryListState = {
  encounters: EncounterSummary[];
  loading: boolean;
  hasMore: boolean;
  error: string | null;
};

export function useHistoryList() {
  const [state, setState] = useState<HistoryListState>({
    encounters: [],
    loading: false,
    hasMore: false,
    error: null,
  });
  const cursorRef = useRef<string | null>(null);
  const loadingRef = useRef(false);

  const loadInitial = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const result = await listEncounters(null, 10);
      cursorRef.current = result.next_cursor;
      setState({
        encounters: result.encounters,
        loading: false,
        hasMore: result.has_more,
        error: null,
      });
    } catch (err: any) {
      setState((s) => ({
        ...s,
        loading: false,
        error: err?.message || "加载失败",
      }));
    } finally {
      loadingRef.current = false;
    }
  }, []);

  const loadMore = useCallback(async () => {
    if (loadingRef.current || !cursorRef.current) return;
    loadingRef.current = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const result = await listEncounters(cursorRef.current, 10);
      cursorRef.current = result.next_cursor;
      setState((s) => ({
        encounters: [...s.encounters, ...result.encounters],
        loading: false,
        hasMore: result.has_more,
        error: null,
      }));
    } catch (err: any) {
      setState((s) => ({
        ...s,
        loading: false,
        error: err?.message || "加载失败",
      }));
    } finally {
      loadingRef.current = false;
    }
  }, []);

  return { state, loadInitial, loadMore };
}
