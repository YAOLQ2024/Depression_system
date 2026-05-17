import { useCallback, useEffect, useRef, useState } from "react";

export type ToastTone = "success" | "warning" | "error";

export type TimedToast = {
  message: string;
  tone: ToastTone;
} | null;

export function useTimedToast(duration = 3000) {
  const [toast, setToast] = useState<TimedToast>(null);
  const timerRef = useRef<number | null>(null);

  const dismissToast = useCallback(() => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setToast(null);
  }, []);

  const pushToast = useCallback(
    (message: string, tone: ToastTone = "success") => {
      if (!message.trim()) {
        return;
      }

      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }

      setToast({ message, tone });
      timerRef.current = window.setTimeout(() => {
        setToast(null);
        timerRef.current = null;
      }, duration);
    },
    [duration],
  );

  useEffect(() => dismissToast, [dismissToast]);

  return {
    toast,
    pushToast,
    dismissToast,
  };
}
