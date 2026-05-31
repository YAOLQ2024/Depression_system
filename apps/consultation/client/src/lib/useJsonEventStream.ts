import { useEffect, useRef, useState, type MutableRefObject } from "react";

type UseJsonEventStreamOptions<T> = {
  url: string | null;
  onMessage: (payload: T) => void;
  enabled?: boolean;
  eventName?: string;
  maxConsecutiveParseFailures?: number;
};

type UseJsonEventStreamResult = {
  isActive: boolean;
  activeRef: MutableRefObject<boolean>;
};

export function useJsonEventStream<T>({
  url,
  onMessage,
  enabled = true,
  eventName = "live_snapshot",
  maxConsecutiveParseFailures = 3,
}: UseJsonEventStreamOptions<T>): UseJsonEventStreamResult {
  const [isActive, setIsActive] = useState(false);
  const activeRef = useRef(false);
  const onMessageRef = useRef(onMessage);
  const parseFailureCountRef = useRef(0);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    if (!enabled || !url || typeof window === "undefined" || typeof EventSource === "undefined") {
      activeRef.current = false;
      setIsActive(false);
      return;
    }

    const eventSource = new EventSource(url, { withCredentials: true });

    const setActive = (next: boolean) => {
      activeRef.current = next;
      setIsActive(next);
    };

    const handleOpen = () => {
      parseFailureCountRef.current = 0;
      setActive(true);
    };

    const handleError = () => {
      setActive(false);
    };

    const handleMessage = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as T;
        parseFailureCountRef.current = 0;
        onMessageRef.current(payload);
      } catch {
        parseFailureCountRef.current += 1;
        if (parseFailureCountRef.current >= maxConsecutiveParseFailures) {
          setActive(false);
          eventSource.close();
        }
      }
    };

    eventSource.addEventListener("open", handleOpen);
    eventSource.addEventListener("error", handleError);
    eventSource.addEventListener(eventName, handleMessage as EventListener);

    return () => {
      setActive(false);
      eventSource.removeEventListener("open", handleOpen);
      eventSource.removeEventListener("error", handleError);
      eventSource.removeEventListener(eventName, handleMessage as EventListener);
      eventSource.close();
    };
  }, [enabled, eventName, maxConsecutiveParseFailures, url]);

  return {
    isActive,
    activeRef,
  };
}
