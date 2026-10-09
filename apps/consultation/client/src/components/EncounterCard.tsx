import { motion } from "motion/react";
import { ArrowRight, Calendar, Clock, FileText, Play, ShieldAlert, ShieldCheck, User } from "lucide-react";
import { cn } from "../lib/utils";
import type { EncounterSummary } from "../services/api/contracts";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  in_progress: "进行中",
  paused: "已暂停",
  completed: "已完成",
};

const FLOW_LABELS: Record<string, string> = {
  consultation: "问诊",
  assessment: "量表评估",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function formatTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function relativeDate(iso: string | null): string {
  if (!iso) return "";
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diffMs = now - then;
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return "今天";
  if (diffDays === 1) return "昨天";
  if (diffDays < 7) return `${diffDays}天前`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}周前`;
  return `${Math.floor(diffDays / 30)}月前`;
}

function riskConfig(level: string | null): { bg: string; text: string; ring: string; label: string } {
  if (!level) return { bg: "bg-slate-50", text: "text-slate-500", ring: "ring-slate-200", label: "未知" };
  if (level === "high" || level === "urgent")
    return { bg: "bg-rose-50", text: "text-rose-600", ring: "ring-rose-200", label: level };
  if (level === "medium")
    return { bg: "bg-amber-50", text: "text-amber-600", ring: "ring-amber-200", label: level };
  return { bg: "bg-emerald-50", text: "text-emerald-600", ring: "ring-emerald-200", label: level };
}

type EncounterCardProps = {
  encounter: EncounterSummary;
  onContinue?: (encounter: EncounterSummary) => void;
  onViewDetail?: (encounter: EncounterSummary) => void;
  index?: number;
};

export function EncounterCard({ encounter, onContinue, onViewDetail, index = 0 }: EncounterCardProps) {
  const isCompleted = encounter.status === "completed";
  const statusLabel = STATUS_LABELS[encounter.status] || encounter.status;
  const flowLabel = FLOW_LABELS[encounter.current_flow_type] || "";
  const risk = riskConfig(encounter.overall_risk_level);

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="group"
    >
      <div
        className={cn(
          "relative overflow-hidden rounded-2xl bg-white transition-all duration-300",
          "shadow-sm ring-1 ring-black/[0.04]",
          "hover:shadow-lg hover:ring-violet-200/60 hover:-translate-y-0.5",
        )}
      >
        {/* 顶部渐变线 */}
        <div
          className={cn(
            "h-[2px] w-full",
            isCompleted
              ? "bg-gradient-to-r from-violet-400 via-blue-400 to-violet-400"
              : "bg-gradient-to-r from-amber-400 via-orange-400 to-amber-400",
          )}
        />

        <div className="portrait-encounter-body flex items-center gap-6 p-5 md:px-6">
          {/* 左侧：状态圆 */}
          <div
            className={cn(
              "hidden h-11 w-11 shrink-0 items-center justify-center rounded-xl md:flex",
              isCompleted
                ? "bg-gradient-to-br from-violet-500 to-blue-500 text-white"
                : "bg-gradient-to-br from-amber-400 to-orange-400 text-white",
            )}
          >
            {isCompleted ? (
              <ShieldCheck className="h-5 w-5" />
            ) : (
              <Clock className="h-5 w-5" />
            )}
          </div>

          {/* 中间：主要信息 */}
          <div className="min-w-0 flex-1">
            {/* 第一行：时间 + 状态 + 阶段 */}
            <div className="mb-1.5 flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1 text-xs text-slate-400">
                <Calendar className="h-3.5 w-3.5" />
                <span>{formatDate(encounter.created_at)}</span>
                <span className="text-slate-300">·</span>
                <span>{formatTime(encounter.created_at)}</span>
              </div>
              <span className="text-[11px] text-slate-300">({relativeDate(encounter.created_at)})</span>
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1",
                  isCompleted
                    ? "bg-violet-50 text-violet-600 ring-violet-200"
                    : "bg-amber-50 text-amber-600 ring-amber-200",
                )}
              >
                {isCompleted ? (
                  <span className="h-1.5 w-1.5 rounded-full bg-violet-500" />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
                )}
                {statusLabel}
              </span>
              {flowLabel && (
                <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-600 ring-1 ring-blue-200">
                  {flowLabel}
                </span>
              )}
            </div>

            {/* 第二行：主诉 */}
            <p className="mb-2 text-sm leading-relaxed text-slate-700 line-clamp-1 md:line-clamp-2">
              {encounter.chief_complaint_summary || "暂无主诉摘要"}
            </p>

            {/* 第三行：指标 */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-2.5 py-1 text-xs text-slate-500">
                <FileText className="h-3.5 w-3.5 text-violet-400" />
                <span>
                  PHQ-9：<span className="font-semibold text-slate-700">{encounter.phq9_score != null ? `${encounter.phq9_score}分` : "—"}</span>
                </span>
              </div>
              <div
                className={cn(
                  "flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium ring-1",
                  risk.bg, risk.text, risk.ring,
                )}
              >
                {encounter.overall_risk_level === "high" || encounter.overall_risk_level === "urgent" ? (
                  <ShieldAlert className="h-3.5 w-3.5" />
                ) : encounter.overall_risk_level ? (
                  <ShieldCheck className="h-3.5 w-3.5" />
                ) : null}
                <span>风险：{risk.label}</span>
              </div>
              {encounter.consultation_session_id && (
                <div className="flex items-center gap-1 rounded-lg bg-slate-50 px-2.5 py-1 text-xs text-slate-400">
                  <User className="h-3 w-3" />
                  <span>问诊会话</span>
                </div>
              )}
            </div>
          </div>

          {/* 右侧：操作 */}
          <div className="shrink-0">
            {isCompleted ? (
              <button
                onClick={() => onViewDetail?.(encounter)}
                className={cn(
                  "flex items-center gap-1.5 rounded-xl px-5 py-2.5 text-xs font-semibold",
                  "bg-gradient-to-r from-violet-500 to-blue-500 text-white",
                  "shadow-sm shadow-violet-500/20 transition-all duration-200",
                  "hover:shadow-md hover:shadow-violet-500/30 hover:-translate-y-px",
                  "cursor-pointer",
                )}
              >
                <span>查看详情</span>
                <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
              </button>
            ) : (
              <button
                onClick={() => onContinue?.(encounter)}
                className={cn(
                  "flex items-center gap-1.5 rounded-xl px-5 py-2.5 text-xs font-semibold",
                  "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
                  "transition-all duration-200 hover:bg-amber-100 hover:-translate-y-px",
                  "cursor-pointer",
                )}
              >
                <Play className="h-3.5 w-3.5" />
                <span>继续</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
