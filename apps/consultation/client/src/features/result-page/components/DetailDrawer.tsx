import { useEffect, useState } from "react";
import { AlertTriangle, BookOpen, Flag, Leaf, Stethoscope, X } from "lucide-react";
import { AdviceCard } from "./AdviceCard";
import { GlassCard } from "./GlassCard";
import { RingChart } from "./RingChart";
import { ScaleItemResultTable } from "./ScaleItemResultTable";
import { SeverityBadge } from "./SeverityBadge";
import { TrendLineChart } from "./TrendLineChart";
import type { ResultDetailPanelData } from "../types";

interface DetailDrawerProps {
  open: boolean;
  detail: ResultDetailPanelData | null;
  onClose: () => void;
}

export function DetailDrawer({ open, detail, onClose }: DetailDrawerProps) {
  const [showItems, setShowItems] = useState(false);

  useEffect(() => {
    if (open) {
      setShowItems(false);
    }
  }, [open, detail?.id]);

  if (!open || !detail) {
    return null;
  }

  const hasItems = (detail.items?.length ?? 0) > 0;

  return (
    <GlassCard className="relative flex h-full w-full flex-col overflow-hidden rounded-[10px] border-white/16 bg-[linear-gradient(180deg,rgba(8,16,32,0.74),rgba(8,16,32,0.52))] shadow-[0_24px_60px_rgba(15,23,42,0.26)] backdrop-blur-[20px]">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),transparent_18%,transparent_82%,rgba(255,255,255,0.03))]" />
      <div className="relative z-10 flex items-start justify-between border-b border-white/30 p-4">
        <div>
          <h2 className="mb-1 text-2xl font-bold text-white">{detail.title}</h2>
          <div className="text-sm font-medium text-sky-100/78">
            {detail.completedAt ? `评估时间 ${detail.completedAt}` : detail.fullName || detail.name || "量表详情"}
          </div>
        </div>
        <button
          onClick={onClose}
          className="flex h-10 w-10 items-center justify-center rounded-full bg-white/[0.08] shadow-sm transition-colors hover:bg-white/[0.16]"
          aria-label="关闭详情抽屉"
        >
          <X className="h-5 w-5 text-white/72" />
        </button>
      </div>

      <div className="relative z-10 min-h-0 flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          <GlassCard className="p-4">
            <div className="grid gap-4 md:grid-cols-3 md:items-center">
              <div className="flex justify-center">
                <RingChart
                  score={detail.score ?? 0}
                  maxScore={detail.maxScore ?? 100}
                  label="本次得分"
                  size={150}
                  strokeWidth={14}
                  valueLabel={detail.score === null ? "--" : undefined}
                />
              </div>
              <div className="flex flex-col items-center justify-center gap-3 text-center">
                <div className="text-sm font-semibold tracking-[0.06em] text-sky-100/82">严重程度</div>
                <SeverityBadge level={detail.severity} className="px-5 py-2 text-base" />
              </div>
              <div className="flex flex-col items-center justify-center gap-3 text-center">
                <div className="text-sm font-semibold tracking-[0.06em] text-sky-100/82">风险提示</div>
                <div className="text-2xl font-bold text-rose-500">{detail.riskLabel || "待补充"}</div>
              </div>
            </div>
          </GlassCard>

          <div className="grid gap-3 md:grid-cols-3">
            <GlassCard className="p-4">
              <div className="mb-1 text-sm font-semibold tracking-[0.06em] text-sky-100/78">标准化得分</div>
              <div className="text-xl font-semibold text-white">
                {detail.normalizedScore !== null && detail.normalizedScore !== undefined
                  ? `${detail.normalizedScore}`
                  : "--"}
              </div>
            </GlassCard>
            <GlassCard className="p-4">
              <div className="mb-1 text-sm font-semibold tracking-[0.06em] text-sky-100/78">题目完成数</div>
              <div className="text-xl font-semibold text-white">
                {detail.answeredItemCount !== null && detail.answeredItemCount !== undefined
                  ? `${detail.answeredItemCount}/${detail.configuredItemCount || "--"}`
                  : detail.configuredItemCount
                    ? `--/${detail.configuredItemCount}`
                    : "--"}
              </div>
            </GlassCard>
            <GlassCard className="p-4">
              <div className="mb-1 text-sm font-semibold tracking-[0.06em] text-sky-100/78">计分说明</div>
              <div className="text-xl font-semibold text-white">{detail.scoreMethodLabel || "待补充"}</div>
            </GlassCard>
          </div>

          {detail.riskFlags?.length ? (
            <GlassCard className="p-4">
              <div className="mb-3 flex items-center gap-2 text-white">
                <Flag className="h-5 w-5 text-rose-500" />
                <h3 className="text-base font-semibold">风险标记</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {detail.riskFlags.map((flag) => (
                  <span
                    key={`${flag.flag}-${flag.itemId || flag.label}`}
                    className="rounded-full border border-rose-200/30 bg-rose-500/12 px-3 py-1 text-sm font-medium text-rose-100"
                  >
                    {flag.label}
                  </span>
                ))}
              </div>
            </GlassCard>
          ) : null}

          {detail.verificationStatus && detail.verificationStatus !== "verified" ? (
            <GlassCard className="border-amber-300/30 bg-amber-400/8 p-4">
              <p className="text-sm leading-6 text-white/78">
                当前量表的计分配置仍带有待复核标记，结果页先按现有后端返回展示，后续以正式 contract 为准。
              </p>
            </GlassCard>
          ) : null}

          <TrendLineChart data={detail.history || []} />

          <div className="grid gap-3 md:grid-cols-2">
            <AdviceCard
              icon={<BookOpen className="h-5 w-5" />}
              title="结果解读"
              content={detail.interpretation || "结果解读待接入。"}
            />
            <AdviceCard
              icon={<AlertTriangle className="h-5 w-5" />}
              title="风险提示"
              content={detail.riskHint || "风险提示待接入。"}
              tone="amber"
            />
            <AdviceCard
              icon={<Stethoscope className="h-5 w-5" />}
              title="就诊建议"
              content={detail.clinicalAdvice || "就诊建议待接入。"}
            />
            <AdviceCard
              icon={<Leaf className="h-5 w-5" />}
              title="生活建议"
              content={detail.lifestyleAdvice || "生活建议待接入。"}
              tone="emerald"
            />
          </div>

          {showItems ? (
            <ScaleItemResultTable items={detail.items || []} notice={detail.itemResultsNotice} />
          ) : null}
        </div>
      </div>

      {!showItems && hasItems ? (
        <div className="relative z-10 border-t border-white/20 bg-transparent p-4">
          <button
            onClick={() => setShowItems(true)}
            className="flex w-full items-center justify-center gap-2 rounded-full bg-[linear-gradient(120deg,rgba(96,165,250,0.95),rgba(99,102,241,0.98),rgba(168,85,247,0.95),rgba(96,165,250,0.95))] px-8 py-3 text-white shadow-[0_18px_50px_rgba(99,102,241,0.28)] transition-all active:scale-95 hover:brightness-110"
          >
            <BookOpen className="h-5 w-5" />
            查看完整报告
          </button>
        </div>
      ) : null}
    </GlassCard>
  );
}
