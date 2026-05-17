import { CircleAlert, CircleCheckBig, Info } from "lucide-react";

import { cn } from "../lib/utils";
import type { TimedToast } from "../lib/useTimedToast";

export function AppToast({
  toast,
  className,
}: {
  toast: TimedToast;
  className?: string;
}) {
  if (!toast) {
    return null;
  }

  return (
    <div className={cn("pointer-events-none fixed top-4 right-4 z-[140] max-w-sm", className)}>
      <div
        className={cn(
          "rounded-2xl border px-4 py-3 shadow-2xl backdrop-blur-sm",
          toast.tone === "error"
            ? "border-red-200 bg-red-50/95 text-red-700"
            : toast.tone === "success"
              ? "border-emerald-200 bg-emerald-50/95 text-emerald-700"
              : "border-indigo-200 bg-white/95 text-slate-700",
        )}
      >
        <div className="flex items-start gap-3">
          <div
            className={cn(
              "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
              toast.tone === "error"
                ? "bg-red-100 text-red-500"
                : toast.tone === "success"
                  ? "bg-emerald-100 text-emerald-500"
                  : "bg-indigo-100 text-indigo-500",
            )}
          >
            {toast.tone === "error" ? (
              <CircleAlert className="h-[13px] w-[13px]" />
            ) : toast.tone === "success" ? (
              <CircleCheckBig className="h-[13px] w-[13px]" />
            ) : (
              <Info className="h-[13px] w-[13px]" />
            )}
          </div>
          <p className="text-xs font-semibold leading-5">{toast.message}</p>
        </div>
      </div>
    </div>
  );
}
