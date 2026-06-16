import { Activity, Layers, Leaf, MessageSquareText, Stethoscope } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../../../lib/utils";
import { getToneClasses } from "../presentation";
import type { ResultModuleCard, ResultScaleBrief } from "../types";
import { AdviceCard } from "./AdviceCard";
import { GlassCard } from "./GlassCard";
import { RingChart } from "./RingChart";
import { ScaleResultList } from "./ScaleResultList";
import { SeverityBadge } from "./SeverityBadge";
import { ResultThemeContext, useResultTheme, themeClasses } from "../theme-context";

interface SummaryDashboardProps {
  title?: string;
  modules: ResultModuleCard[];
  overallScore?: number | null;
  overallScoreLabel?: string;
  overallSeverity?: string | null;
  overallRiskLevel?: string | null;
  overallRiskReason?: string | null;
  scales: ResultScaleBrief[];
  selectedScaleId: string | null;
  onOpenScaleDetail: (id: string) => void;
  clinicalAdvice?: string | null;
  lifestyleAdvice?: string | null;
  compact?: boolean;
  theme?: "dark" | "light";
}

function getFallbackModuleIcon(index: number): ReactNode {
  const icons = [MessageSquareText, Activity, Layers];
  const Icon = icons[index % icons.length];
  return <Icon className="h-6 w-6" />;
}

function DashboardInner({
  title,
  modules,
  overallScore,
  overallScoreLabel,
  overallSeverity,
  overallRiskLevel,
  overallRiskReason,
  scales,
  selectedScaleId,
  onOpenScaleDetail,
  clinicalAdvice,
  lifestyleAdvice,
  compact,
}: Omit<SummaryDashboardProps, "theme">) {
  const theme = useResultTheme();
  const t = themeClasses;

  return (
    <div className="flex h-full flex-col space-y-2">
      <div className="flex items-center justify-between">
        <h1 className={cn("text-2xl font-bold tracking-tight", t.title[theme])}>{title}</h1>
      </div>

      <div className={cn("grid gap-2", compact ? "grid-cols-3" : modules.length >= 3 ? "md:grid-cols-3" : "md:grid-cols-2")}>
        {modules.map((module, index) => {
          const toneClasses = getToneClasses(module.tone || "blue");
          return (
            <GlassCard key={module.id} className={cn(compact ? "p-3" : "p-4")}>
              <div className={cn("flex gap-3", compact ? "h-full flex-col" : "items-start justify-between")}>
                <div className={cn("flex min-w-0 gap-3", compact ? "items-start" : "items-center")}>
                  <div className={cn("flex shrink-0 items-center justify-center rounded-full", compact ? "h-10 w-10" : "h-12 w-12", toneClasses.iconBg, toneClasses.iconText)}>
                    <div className={cn(compact ? "scale-90" : "")}>{module.icon || getFallbackModuleIcon(index)}</div>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className={cn("mb-1 font-semibold tracking-[0.06em]", t.subtitle[theme], compact ? "text-[13px]" : "text-sm")}>
                      {module.name}
                    </div>
                    {module.value !== undefined && module.value !== null ? (
                      <>
                        <div className={cn("truncate font-bold leading-none", t.value[theme], compact ? "text-2xl" : "text-3xl")}>
                          {module.value}
                        </div>
                        {module.description ? (
                          <div className={cn("mt-2", t.muted[theme], compact ? "line-clamp-3 text-xs leading-5" : "text-sm leading-relaxed")}>
                            {module.description}
                          </div>
                        ) : null}
                      </>
                    ) : (
                      <div className={cn(t.muted[theme], compact ? "line-clamp-4 text-xs leading-5" : "text-sm leading-relaxed")}>
                        {module.description || "内容待接入"}
                      </div>
                    )}
                  </div>
                </div>
                {module.onAction && module.actionLabel ? (
                  <button
                    onClick={module.onAction}
                    className={cn("shrink-0 rounded-full border font-medium transition-colors", t.actionBtn[theme], compact ? "self-start px-2.5 py-1 text-xs" : "px-3 py-1 text-sm")}
                  >
                    {module.actionLabel}
                  </button>
                ) : null}
              </div>
            </GlassCard>
          );
        })}
      </div>

      <GlassCard className="p-4">
        <div className="grid gap-4 md:grid-cols-[minmax(220px,0.95fr)_1px_minmax(0,0.85fr)_1px_minmax(0,0.85fr)] md:items-center">
          <div className="flex justify-center">
          <RingChart
            score={overallScore ?? 0}
            label={overallScoreLabel}
            size={150}
            strokeWidth={14}
            valueLabel={overallScore === null ? "--" : undefined}
          />
          </div>
          <div className={cn("hidden h-24 w-px md:block", theme === "dark" ? "bg-gradient-to-b from-transparent via-white/15 to-transparent" : "bg-gradient-to-b from-transparent via-slate-200 to-transparent")} />
          <div className="flex flex-col items-center text-center md:items-start md:text-left">
            <div className={cn("mb-4 text-sm font-semibold tracking-[0.06em]", t.subtitle[theme])}>疾病严重程度</div>
            <SeverityBadge
              level={overallSeverity || "待接入"}
              className="px-5 py-3 text-xl font-semibold tracking-wide md:text-2xl"
            />
          </div>
          <div className={cn("hidden h-24 w-px md:block", theme === "dark" ? "bg-gradient-to-b from-transparent via-white/15 to-transparent" : "bg-gradient-to-b from-transparent via-slate-200 to-transparent")} />
          <div className="flex flex-col items-center text-center md:items-start md:text-left">
            <div className={cn("mb-4 text-sm font-semibold tracking-[0.06em]", t.subtitle[theme])}>风险等级</div>
            <SeverityBadge
              level={overallRiskLevel || "待接入"}
              className="px-5 py-3 text-xl font-semibold tracking-wide md:text-2xl"
            />
            {overallRiskReason ? (
              <p
                className={cn(
                  "mt-3 max-w-[24rem] text-xs leading-6 md:text-sm",
                  t.body[theme],
                )}
              >
                {overallRiskReason}
              </p>
            ) : null}
          </div>
        </div>
      </GlassCard>

      <ScaleResultList scales={scales} selectedScaleId={selectedScaleId} onScaleSelect={onOpenScaleDetail} />

      <div className="mt-auto grid gap-3 md:grid-cols-2">
        <AdviceCard icon={<Stethoscope className="h-5 w-5" />} title="就诊建议" content={clinicalAdvice || "就诊建议待接入。"} />
        <AdviceCard icon={<Leaf className="h-5 w-5" />} title="生活建议" content={lifestyleAdvice || "生活建议待接入。"} tone="emerald" />
      </div>
    </div>
  );
}

export function SummaryDashboard({ theme = "dark", ...props }: SummaryDashboardProps) {
  return (
    <ResultThemeContext.Provider value={theme}>
      <DashboardInner {...props} />
    </ResultThemeContext.Provider>
  );
}
