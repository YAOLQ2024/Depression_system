import { ClipboardList, Sparkles, X } from "lucide-react";
import type { ResultConsultationSummary } from "../types";
import { GlassCard } from "./GlassCard";

interface ConsultationSummaryDrawerProps {
  open: boolean;
  summary: ResultConsultationSummary | null;
  onClose: () => void;
}

export function ConsultationSummaryDrawer({
  open,
  summary,
  onClose,
}: ConsultationSummaryDrawerProps) {
  if (!open || !summary) {
    return null;
  }

  return (
    <GlassCard className="relative flex h-full w-full flex-col overflow-hidden rounded-[10px] border-white/16 bg-[linear-gradient(180deg,rgba(8,16,32,0.74),rgba(8,16,32,0.52))] shadow-[0_24px_60px_rgba(15,23,42,0.26)] backdrop-blur-[20px]">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),transparent_18%,transparent_82%,rgba(255,255,255,0.03))]" />
      <div className="relative z-10 flex items-start justify-between border-b border-white/30 p-4">
        <div>
          <h2 className="mb-1 text-2xl font-bold text-white">{summary.title}</h2>
          <div className="text-sm font-medium text-sky-100/78">{summary.description}</div>
        </div>
        <button
          onClick={onClose}
          className="flex h-10 w-10 items-center justify-center rounded-full bg-white/[0.08] shadow-sm transition-colors hover:bg-white/[0.16]"
          aria-label="关闭咨询摘要详情"
        >
          <X className="h-5 w-5 text-white/72" />
        </button>
      </div>

      <div className="relative z-10 min-h-0 flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          <GlassCard className="border-primary-300/28 bg-primary-500/8 p-4">
            <div className="mb-2 flex items-center gap-2 text-primary-200">
              <Sparkles className="h-5 w-5" />
              <h3 className="text-base font-semibold">整体咨询总结</h3>
            </div>
            <p className="text-sm leading-7 text-white/78">{summary.overallSummary}</p>
          </GlassCard>

          {summary.sections.map((section) => (
            <GlassCard key={section.id} className="p-4">
              <div className="mb-2 flex items-center gap-2 text-white">
                <ClipboardList className="h-5 w-5 text-primary-600" />
                <h3 className="text-base font-semibold">{section.title}</h3>
              </div>
              <p className="text-sm leading-7 text-white/74">{section.content}</p>
            </GlassCard>
          ))}

          {summary.requiredScaleLabels.length ? (
            <GlassCard className="p-4">
              <h3 className="mb-3 text-base font-semibold text-white">关联量表</h3>
              <div className="flex flex-wrap gap-2">
                {summary.requiredScaleLabels.map((label) => (
                  <span
                    key={label}
                    className="rounded-full border border-primary-300/28 bg-primary-500/10 px-3 py-1 text-sm font-medium text-primary-100"
                  >
                    {label}
                  </span>
                ))}
              </div>
            </GlassCard>
          ) : null}

          <GlassCard className="border-amber-300/30 bg-amber-400/8 p-4">
            <p className="text-sm leading-7 text-white/74">
              咨询会话部分只展示摘要报告，不展示机器评分。本摘要用于帮助回看本轮问诊过程与阶段性结论。
            </p>
          </GlassCard>
        </div>
      </div>
    </GlassCard>
  );
}
