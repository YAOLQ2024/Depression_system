import { useEffect, useState } from "react";
import {
  getEegExplanation,
  getEegExplanationHistory,
  getEegWindows,
  requestEegExplanation,
} from "../../services/api/eeg.api";
import type {
  EegClass,
  EegExplanation,
  EegHistoryPage,
  EegWindowRecord,
} from "./eegMirrorTypes";

export function useEegMirrorData(
  sessionId: string | null | undefined,
  latestId: string | null | undefined,
  target: EegClass,
  enabled: boolean,
  explanationUpdate?: string,
) {
  const [windowsState, setWindows] = useState<{
    session: string;
    items: EegWindowRecord[];
  }>({ session: "", items: [] });
  const [pinned, setPinned] = useState<{
    session: string;
    window: EegWindowRecord;
  } | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [historyState, setHistory] = useState<{
    key: string;
    data: EegHistoryPage;
  } | null>(null);
  const [detailState, setDetail] = useState<{
    key: string;
    data: EegExplanation;
  } | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const windows = windowsState.session === sessionId ? windowsState.items : [];
  const selection =
    pinned && pinned.session === sessionId
      ? pinned.window
      : (windows.find(
          (item) => item.prediction_status === "ready" && item.inference_id,
        ) ?? null);
  const historyKey = `${sessionId}:${target}:${cursor || "latest"}`;
  const detailKey = `${sessionId}:${target}:${selection?.inference_id || ""}`;
  const history = historyState?.key === historyKey ? historyState.data : null;
  const detail = detailState?.key === detailKey ? detailState.data : null;

  useEffect(() => {
    setPinned(null);
    setCursor(null);
    setHistory(null);
    setDetail(null);
    setError("");
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    const controller = new AbortController();
    let timer: number;
    const load = async () => {
      try {
        const data = await getEegWindows(sessionId, controller.signal);
        if (!controller.signal.aborted) {
          setWindows({ session: sessionId, items: data.items });
          setError("");
        }
      } catch (e) {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : "历史记录读取失败");
      }
      if (!controller.signal.aborted) timer = window.setTimeout(load, 15000);
    };
    void load();
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [sessionId, latestId, refresh]);

  useEffect(() => {
    if (!sessionId || !enabled) return;
    const controller = new AbortController();
    let timer: number;
    const load = async () => {
      try {
        const data = await getEegExplanationHistory(
          sessionId,
          target,
          cursor,
          controller.signal,
        );
        if (!controller.signal.aborted) {
          setHistory({ key: historyKey, data });
          setError("");
        }
      } catch (e) {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : "解释历史读取失败");
      }
      if (!controller.signal.aborted) timer = window.setTimeout(load, 4000);
    };
    void load();
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [
    sessionId,
    target,
    cursor,
    historyKey,
    latestId,
    enabled,
    refresh,
    explanationUpdate,
  ]);

  useEffect(() => {
    if (!sessionId || !selection?.inference_id || !enabled) return;
    const controller = new AbortController();
    let timer: number;
    const accept = (data: EegExplanation) => {
      if (controller.signal.aborted) return;
      if (
        data.inference_id !== selection.inference_id ||
        data.config.target_class !== target ||
        data.sample_id !== selection.sample_id
      ) {
        setError("解释与所选片段不一致，请重试。");
        return;
      }
      setDetail({ key: detailKey, data });
      if (data.status === "queued" || data.status === "running")
        timer = window.setTimeout(() => {
          void poll(data.explanation_id);
        }, 1500);
    };
    const fail = (e: unknown) => {
      if (!controller.signal.aborted)
        setError(e instanceof Error ? e.message : "解释读取失败");
    };
    const poll = async (id: string) => {
      try {
        accept(await getEegExplanation(sessionId, id, controller.signal));
      } catch (e) {
        fail(e);
      }
    };
    void requestEegExplanation(
      sessionId,
      selection.inference_id,
      target,
      controller.signal,
    )
      .then(accept)
      .catch(fail);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [
    sessionId,
    selection?.inference_id,
    selection?.sample_id,
    target,
    detailKey,
    enabled,
    refresh,
    explanationUpdate,
  ]);

  return {
    windows,
    history,
    detail,
    selection,
    error,
    following: !pinned || pinned.session !== sessionId,
    pin: (item: EegWindowRecord) =>
      setPinned({ session: sessionId || "", window: item }),
    follow: () => {
      setPinned(null);
      setCursor(null);
    },
    resetTarget: () => {
      setCursor(null);
    },
    older: () => {
      if (history?.next_cursor) setCursor(history.next_cursor);
    },
    firstPage: () => setCursor(null),
    isOlder: Boolean(cursor),
    retry: () => {
      setDetail(null);
      setError("");
      setRefresh((v) => v + 1);
    },
  };
}
