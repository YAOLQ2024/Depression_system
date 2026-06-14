import { Brain, ChevronRight, FileText, Moon, Smile } from "lucide-react";
import { cn } from "../../../lib/utils";
import { getScaleTone, getToneClasses } from "../presentation";
import type { ResultScaleBrief } from "../types";
import { GlassCard } from "./GlassCard";
import { SeverityBadge } from "./SeverityBadge";
import { useResultTheme, themeClasses } from "../theme-context";

interface ScaleResultListProps {
  scales: ResultScaleBrief[];
  selectedScaleId: string | null;
  onScaleSelect: (id: string) => void;
}

function getScaleIcon(index: number) {
  switch (index % 4) {
    case 0: return FileText;
    case 1: return Smile;
    case 2: return Moon;
    case 3: return Brain;
    default: return FileText;
  }
}

export function ScaleResultList({ scales, selectedScaleId, onScaleSelect }: ScaleResultListProps) {
  const theme = useResultTheme();
  const t = themeClasses;

  return (
    <GlassCard className="p-3">
      <h3 className={cn("mb-3 text-base font-semibold", t.title[theme])}>量表结果</h3>
      <div className="flex flex-col gap-2">
        {scales.map((scale, index) => {
          const tone = getScaleTone(index);
          const toneClasses = getToneClasses(tone);
          const Icon = getScaleIcon(index);
          const scoreLabel = scale.scoreLabel ?? (typeof scale.score === "number" ? `${scale.score}分` : "--");

          return (
            <div
              key={scale.id}
              onClick={() => onScaleSelect(scale.id)}
              className={cn(
                "group flex cursor-pointer items-center justify-between rounded-[8px] border p-3 transition-colors",
                selectedScaleId === scale.id ? t.scaleRowActive[theme] : t.scaleRow[theme],
              )}
            >
              <div className="flex w-[180px] items-center gap-3">
                <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-full", toneClasses.iconBg, toneClasses.iconText)}>
                  <Icon className="h-5 w-5" />
                </div>
                <span className={cn("font-medium", theme === "dark" ? "text-white/92" : "text-slate-700")}>{scale.name}</span>
              </div>

              <div className={cn("w-[88px] text-left text-sm font-medium", t.scoreValue[theme])}>{scoreLabel}</div>

              <div className="w-[108px]">
                <SeverityBadge level={scale.severity} />
              </div>

              <div className={cn("flex w-[104px] items-center justify-end gap-1 text-sm font-medium", t.detailLink[theme])}>
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
