import { Brain, ChevronRight, FileText, Moon, Smile } from "lucide-react";
import { cn } from "../../../lib/utils";
import { getScaleTone, getToneClasses } from "../presentation";
import type { ResultScaleBrief } from "../types";
import { GlassCard } from "./GlassCard";
import { SeverityBadge } from "./SeverityBadge";

interface ScaleResultListProps {
  scales: ResultScaleBrief[];
  selectedScaleId: string | null;
  onScaleSelect: (id: string) => void;
}

function getScaleIcon(index: number) {
  switch (index % 4) {
    case 0:
      return FileText;
    case 1:
      return Smile;
    case 2:
      return Moon;
    case 3:
      return Brain;
    default:
      return FileText;
  }
}

export function ScaleResultList({ scales, selectedScaleId, onScaleSelect }: ScaleResultListProps) {
  return (
    <GlassCard className="p-3">
      <h3 className="mb-3 text-base font-semibold text-white">量表结果</h3>
      <div className="flex flex-col gap-2">
        {scales.map((scale, index) => {
          const tone = getScaleTone(index);
          const toneClasses = getToneClasses(tone);
          const Icon = getScaleIcon(index);
          const scoreLabel =
            scale.scoreLabel ?? (typeof scale.score === "number" ? `${scale.score}分` : "--");

          return (
            <div
              key={scale.id}
              onClick={() => onScaleSelect(scale.id)}
              className={cn(
                "group flex cursor-pointer items-center justify-between rounded-[8px] border p-3 transition-colors",
                selectedScaleId === scale.id
                  ? "border-primary-300/70 bg-primary-500/10"
                  : "border-white/10 bg-white/[0.03] hover:bg-white/[0.08]",
              )}
            >
              <div className="flex w-[180px] items-center gap-3">
                <div
                  className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
                    toneClasses.iconBg,
                    toneClasses.iconText,
                  )}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                <span className="font-medium text-white/92">{scale.name}</span>
              </div>

              <div className="w-[88px] text-left text-sm font-medium text-sky-100/82">{scoreLabel}</div>

              <div className="w-[108px]">
                <SeverityBadge level={scale.severity} />
              </div>

              <div className="flex w-[104px] items-center justify-end gap-1 text-sm font-medium text-primary-200">
                <span>查看详情</span>
                <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}
