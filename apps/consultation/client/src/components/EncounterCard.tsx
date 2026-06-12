import { cn } from "../lib/utils";
import type { EncounterSummary } from "../services/api/contracts";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  in_progress: "进行中",
  paused: "已暂停",
  completed: "已完成",
};

const FLOW_LABELS: Record<string, string> = {
  consultation: "问诊阶段",
  assessment: "量表评估阶段",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function statusColor(status: string): string {
  if (status === "completed") return "border-l-emerald-400";
  return "border-l-amber-400";
}

function riskColor(level: string | null): string {
  if (!level) return "text-slate-400";
  if (level === "high" || level === "urgent") return "text-red-400";
  if (level === "medium") return "text-amber-400";
  return "text-emerald-400";
}

type EncounterCardProps = {
  encounter: EncounterSummary;
  onContinue?: (encounter: EncounterSummary) => void;
  onViewDetail?: (encounter: EncounterSummary) => void;
  detailDisabled?: boolean;
};

export function EncounterCard({ encounter, onContinue, onViewDetail, detailDisabled = false }: EncounterCardProps) {
  const isCompleted = encounter.status === "completed";
  const statusLabel = STATUS_LABELS[encounter.status] || encounter.status;
  const flowLabel = FLOW_LABELS[encounter.current_flow_type] || "";

  return (
    <div
      className={cn(
        "rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-4 md:p-5",
        "border-l-4 transition-all hover:bg-white/8",
        statusColor(encounter.status),
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-sm text-slate-300">{formatDate(encounter.created_at)}</span>
            <span
              className={cn(
                "text-xs px-2 py-0.5 rounded-full",
                isCompleted
                  ? "bg-emerald-500/15 text-emerald-400"
                  : "bg-amber-500/15 text-amber-400",
              )}
            >
              {statusLabel}
              {!isCompleted && flowLabel ? `（${flowLabel}）` : ""}
            </span>
          </div>

          <p className="text-sm text-slate-200 truncate mb-2">
            {encounter.chief_complaint_summary || "暂无主诉摘要"}
          </p>

          <div className="flex items-center gap-4 text-xs text-slate-400">
            <span>
              PHQ-9：{encounter.phq9_score != null ? `${encounter.phq9_score}分` : "—"}
            </span>
            <span className={riskColor(encounter.overall_risk_level)}>
              风险：{encounter.overall_risk_level || "—"}
            </span>
          </div>
        </div>

        <div className="shrink-0">
          {isCompleted ? (
            <button
              onClick={() => onViewDetail?.(encounter)}
              disabled={detailDisabled}
              title={detailDisabled ? "详情页即将上线" : undefined}
              className={cn(
                "text-xs transition-colors",
                detailDisabled
                  ? "text-slate-500 cursor-not-allowed opacity-60"
                  : "text-indigo-400 hover:text-indigo-300",
              )}
            >
              查看详情 →
            </button>
          ) : (
            <button
              onClick={() => onContinue?.(encounter)}
              className="text-xs text-amber-400 hover:text-amber-300 transition-colors font-medium"
            >
              继续 →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
