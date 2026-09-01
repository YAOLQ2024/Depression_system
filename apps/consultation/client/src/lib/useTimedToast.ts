import { useCallback, useEffect, useRef, useState } from "react";
import { reportSystemError } from "./systemNotifications";

export type ToastTone = "success" | "warning" | "error";

export type TimedToast = {
  message: string;
  tone: ToastTone;
} | null;

type ToastDurations = Partial<Record<ToastTone, number>>;

type PushToastOptions = {
  durationMs?: number;
};

const DEFAULT_TOAST_DURATIONS: Record<ToastTone, number> = {
  success: 3000,
  warning: 4000,
  error: 5000,
};

export function useTimedToast(durations?: ToastDurations) {
  const [toast, setToast] = useState<TimedToast>(null);
  const timerRef = useRef<number | null>(null);
  const resolvedDurations = {
    ...DEFAULT_TOAST_DURATIONS,
    ...(durations || {}),
  };

  const dismissToast = useCallback(() => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setToast(null);
  }, []);

  const pushToast = useCallback(
    (
      message: string,
      tone: ToastTone = "success",
      options?: PushToastOptions,
    ) => {
      if (!message.trim()) {
        return;
      }

      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }

      setToast({ message, tone });
      if (tone === "error") {
        reportSystemError(message);
      }
      const durationMs =
        options?.durationMs ?? resolvedDurations[tone] ?? resolvedDurations.success;
      timerRef.current = window.setTimeout(() => {
        setToast(null);
        timerRef.current = null;
      }, durationMs);
    },
    [resolvedDurations.error, resolvedDurations.success, resolvedDurations.warning],
  );

  useEffect(() => dismissToast, [dismissToast]);

  return {
    toast,
    pushToast,
    dismissToast,
  };
}
