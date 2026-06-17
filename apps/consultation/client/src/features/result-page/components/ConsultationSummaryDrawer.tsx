import { ClipboardList, Sparkles, X } from "lucide-react";
import { cn } from "../../../lib/utils";
import { ResultThemeContext, type ResultTheme } from "../theme-context";
import type { ResultConsultationSummary } from "../types";
import { GlassCard } from "./GlassCard";

interface ConsultationSummaryDrawerProps {
  open: boolean;
  summary: ResultConsultationSummary | null;
  onClose: () => void;
  theme?: ResultTheme;
}

export function ConsultationSummaryDrawer({
  open,
  summary,
  onClose,
  theme = "dark",
}: ConsultationSummaryDrawerProps) {
  if (!open || !summary) {
    return null;
  }

  return (
    <ResultThemeContext.Provider value={theme}>
      <GlassCard
        className={cn(
          "relative flex h-full w-full flex-col overflow-hidden backdrop-blur-[20px]",
          theme === "dark"
            ? "rounded-[10px] border-white/16 bg-[linear-gradient(180deg,rgba(8,16,32,0.74),rgba(8,16,32,0.52))] shadow-[0_24px_60px_rgba(15,23,42,0.26)]"
            : "rounded-2xl border border-slate-200/70 bg-white/92 shadow-[0_24px_60px_rgba(15,23,42,0.12)]",
        )}
      >
        {theme === "dark" ? (
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),transparent_18%,transparent_82%,rgba(255,255,255,0.03))]" />
        ) : null}

        <div
          className={cn(
            "relative z-10 flex items-start justify-between border-b",
            theme === "dark" ? "border-white/30 p-4" : "border-slate-100 px-5 py-4 md:px-6",
          )}
        >
          <div>
            <h2 className={cn("mb-1 text-2xl font-bold", theme === "dark" ? "text-white" : "text-slate-900")}>
              {summary.title}
            </h2>
            <div className={cn("text-sm font-medium", theme === "dark" ? "text-sky-100/78" : "text-slate-500")}>
              {summary.description}
            </div>
          </div>
          <button
            onClick={onClose}
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-full shadow-sm transition-colors",
              theme === "dark"
                ? "bg-white/[0.08] hover:bg-white/[0.16]"
                : "bg-slate-100 hover:bg-slate-200/80",
            )}
            aria-label="关闭咨询摘要详情"
          >
            <X className={cn("h-5 w-5", theme === "dark" ? "text-white/72" : "text-slate-500")} />
          </button>
        </div>

        <div className={cn("relative z-10 min-h-0 flex-1 overflow-y-auto", theme === "dark" ? "p-4" : "p-5 md:p-6")}>
          <div className="space-y-4">
            <GlassCard
              className={cn(
                "p-4",
                theme === "dark"
                  ? "border-primary-300/28 bg-primary-500/8"
                  : "border border-violet-100 bg-violet-50/90 ring-0 shadow-none",
              )}
            >
              <div className={cn("mb-2 flex items-center gap-2", theme === "dark" ? "text-primary-200" : "text-violet-600")}>
                <Sparkles className="h-5 w-5" />
                <h3 className="text-base font-semibold">整体咨询总结</h3>
              </div>
              <p className={cn("text-sm leading-7", theme === "dark" ? "text-white/78" : "text-slate-600")}>
                {summary.overallSummary}
              </p>
            </GlassCard>

            {summary.sections.map((section) => (
              <GlassCard key={section.id} className="p-4">
                <div className={cn("mb-2 flex items-center gap-2", theme === "dark" ? "text-white" : "text-slate-900")}>
                  <ClipboardList className="h-5 w-5 text-primary-600" />
                  <h3 className="text-base font-semibold">{section.title}</h3>
                </div>
                <p className={cn("text-sm leading-7", theme === "dark" ? "text-white/74" : "text-slate-500")}>
                  {section.content}
                </p>
              </GlassCard>
            ))}

            {summary.linkedScaleLabels.length ? (
              <GlassCard className="p-4">
                <h3 className={cn("mb-3 text-base font-semibold", theme === "dark" ? "text-white" : "text-slate-900")}>关联量表</h3>
                <div className="flex flex-wrap gap-2">
                  {summary.linkedScaleLabels.map((label) => (
                    <span
                      key={label}
                      className={cn(
                        "rounded-full border px-3 py-1 text-sm font-medium",
                        theme === "dark"
                          ? "border-primary-300/28 bg-primary-500/10 text-primary-100"
                          : "border-violet-200 bg-violet-50 text-violet-600",
                      )}
                    >
                      {label}
                    </span>
                  ))}
                </div>
              </GlassCard>
            ) : null}

            <GlassCard
              className={cn(
                "p-4",
                theme === "dark"
                  ? "border-amber-300/30 bg-amber-400/8"
                  : "border border-amber-200 bg-amber-50/90 ring-0 shadow-none",
              )}
            >
              <p className={cn("text-sm leading-7", theme === "dark" ? "text-white/74" : "text-amber-700")}>
                咨询会话部分只展示摘要报告，不展示机器评分。本摘要用于帮助回看本轮问诊过程与阶段性结论。
              </p>
            </GlassCard>
          </div>
        </div>
      </GlassCard>
    </ResultThemeContext.Provider>
  );
}
