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

function InfoTooltip({ children, content }: { children: ReactNode; content: readonly string[] }) {
  return (
    <div tabIndex={0} className="group relative inline-flex cursor-help outline-none">
      <div className="inline-flex border-b border-dotted border-current/45">{children}</div>
      <div
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-50 mb-2 w-80 rounded-md border border-white/15 bg-slate-950 px-3 py-2 text-left text-xs leading-5 font-normal text-white opacity-0 shadow-[0_8px_22px_rgba(0,0,0,0.5)] transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
      >
        {content.map((line) => (
          <span key={line} className="block whitespace-nowrap">{line}</span>
        ))}
      </div>
    </div>
  );
}

const TOOLTIP_CONTENT = {
  overall: [
    "综合评分范围为 0–100 分。",
    "默认由量表评分占 80%、多模态评分占 20% 加权得到。",
    "缺少某类数据时，系统会按可用数据重新计算权重。",
  ],
  severity: [
    "抑郁程度按综合评分划分。",
    "0–24.99 分：无或极轻度抑郁倾向。",
    "25–49.99 分：轻度抑郁倾向。",
    "50–69.99 分：中度抑郁倾向。",
    "70–84.99 分：中重度抑郁倾向。",
    "85–100 分：重度抑郁倾向。",
  ],
  assessment: [
    "量表评分范围为 0–100 分。",
    "各已完成量表会先按自身量程标准化。",
    "系统再按当前量表权重汇总评分。",
    "只有一份量表时，显示该量表的标准化得分。",
  ],
  multimodal: [
    "多模态评分范围为 0–100 分。",
    "综合脑电、文本、语音、表情和姿态等可用信号。",
    "各信号的识别置信度会调整其计算权重。",
  ],
} as const;

function getModuleScoreTooltip(moduleId: string) {
  if (moduleId === "assessment-session") {
    return TOOLTIP_CONTENT.assessment;
  }
  if (moduleId === "multimodal-session") {
    return TOOLTIP_CONTENT.multimodal;
  }
  return null;
}

function DashboardInner({
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
    <div className="flex h-full flex-col space-y-4">
      <GlassCard
        className={cn(
          "shrink-0 border-sky-300/25 bg-[linear-gradient(135deg,rgba(19,42,80,0.92),rgba(10,22,43,0.96)_54%,rgba(25,22,59,0.94))]",
          compact ? "p-3" : "p-4 md:p-5",
        )}
      >
        <div className={cn("mb-4 flex items-start justify-between gap-4", compact && "mb-3")}>
          <div>
            <p className="text-xs font-semibold tracking-[0.18em] text-sky-200/90">最终结果</p>
            <h1 className={cn("mt-1 font-bold tracking-tight", t.title[theme], compact ? "text-xl" : "text-2xl")}>综合评估结论</h1>
            <p className={cn("mt-1 text-xs leading-5 md:text-sm", t.muted[theme])}>已综合问诊、量表及多模态信息生成本次评估结论。</p>
          </div>
          <span className="shrink-0 rounded-full border border-sky-200/25 bg-sky-300/10 px-3 py-1 text-xs font-medium text-sky-100">已完成评估</span>
        </div>

        <div className={cn("grid gap-4", compact ? "grid-cols-3" : "md:grid-cols-[minmax(150px,0.7fr)_minmax(0,0.85fr)_minmax(0,1.1fr)] md:items-center")}>
          <div className={cn("flex justify-center", compact ? "items-start" : "md:justify-start")}>
            <InfoTooltip content={TOOLTIP_CONTENT.overall}>
              <RingChart
                score={overallScore ?? 0}
                label={overallScoreLabel || "综合评分"}
                size={compact ? 112 : 138}
                strokeWidth={compact ? 11 : 13}
                valueLabel={overallScore === null ? "--" : undefined}
              />
            </InfoTooltip>
          </div>

          <div className={cn("flex flex-col", compact ? "items-start" : "items-center text-center md:items-start md:text-left")}>
            <div className={cn("mb-3 text-sm font-semibold tracking-[0.06em]", t.subtitle[theme])}>抑郁程度</div>
            <InfoTooltip content={TOOLTIP_CONTENT.severity}>
              <SeverityBadge level={overallSeverity || "待接入"} className={cn(compact ? "px-3 py-2 text-base" : "px-5 py-3 text-xl font-semibold tracking-wide md:text-2xl")} />
            </InfoTooltip>
            <p className={cn("mt-3 text-xs leading-5 md:text-sm", t.muted[theme])}>请结合下方评估依据与专业人员意见理解结果。</p>
          </div>

          <div className={cn("flex flex-col", compact ? "items-start" : "items-center text-center md:items-start md:text-left")}>
            <div className={cn("mb-3 text-sm font-semibold tracking-[0.06em]", t.subtitle[theme])}>风险等级</div>
            <SeverityBadge level={overallRiskLevel || "待接入"} className={cn(compact ? "px-3 py-2 text-base" : "px-5 py-3 text-xl font-semibold tracking-wide md:text-2xl")} />
            {overallRiskReason ? (
              <p className={cn("mt-3 max-w-[30rem] text-xs leading-5 md:text-sm md:leading-6", t.body[theme])}>{overallRiskReason}</p>
            ) : (
              <p className={cn("mt-3 text-xs leading-5 md:text-sm", t.muted[theme])}>未发现需要补充说明的风险触发因素。</p>
            )}
          </div>
        </div>
      </GlassCard>

      <section className="shrink-0">
        <div className="mb-2">
          <h2 className={cn("text-base font-semibold", t.title[theme])}>评估依据</h2>
          <p className={cn("mt-0.5 text-xs", t.muted[theme])}>以下结果已纳入本次综合评估，不单独作为最终结论。</p>
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
                      <div className={cn("mb-1 font-semibold tracking-[0.06em]", t.subtitle[theme], compact ? "text-[13px]" : "text-sm")}>{module.name}</div>
                      {module.value !== undefined && module.value !== null ? (
                        <>
                          {getModuleScoreTooltip(module.id) ? (
                            <InfoTooltip content={getModuleScoreTooltip(module.id)}>
                              <div className={cn("truncate font-bold leading-none", t.value[theme], compact ? "text-2xl" : "text-3xl")}>{module.value}</div>
                            </InfoTooltip>
                          ) : (
                            <div className={cn("truncate font-bold leading-none", t.value[theme], compact ? "text-2xl" : "text-3xl")}>{module.value}</div>
                          )}
                          {module.description ? <div className={cn("mt-2", t.muted[theme], compact ? "line-clamp-3 text-xs leading-5" : "text-sm leading-relaxed")}>{module.description}</div> : null}
                        </>
                      ) : (
                        <div className={cn(t.muted[theme], compact ? "line-clamp-4 text-xs leading-5" : "text-sm leading-relaxed")}>{module.description || "内容待接入"}</div>
                      )}
                    </div>
                  </div>
                  {module.onAction && module.actionLabel ? (
                    <button onClick={module.onAction} className={cn("shrink-0 rounded-full border font-medium transition-colors", t.actionBtn[theme], compact ? "self-start px-2.5 py-1 text-xs" : "px-3 py-1 text-sm")}>
                      {module.actionLabel}
                    </button>
                  ) : null}
                </div>
              </GlassCard>
            );
          })}
        </div>
      </section>

      <section className="shrink-0">
        <div className="mb-2">
          <h2 className={cn("text-base font-semibold", t.title[theme])}>量表明细</h2>
          <p className={cn("mt-0.5 text-xs", t.muted[theme])}>查看每份量表的得分、等级与逐题作答。</p>
        </div>
        <ScaleResultList scales={scales} selectedScaleId={selectedScaleId} onScaleSelect={onOpenScaleDetail} />
      </section>

      <section className="mt-auto shrink-0">
        <div className="mb-2">
          <h2 className={cn("text-base font-semibold", t.title[theme])}>后续建议</h2>
          <p className={cn("mt-0.5 text-xs", t.muted[theme])}>请优先依据综合评估结论采取下一步行动。</p>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <AdviceCard icon={<Stethoscope className="h-5 w-5" />} title="就诊建议" content={clinicalAdvice || "就诊建议待接入。"} />
          <AdviceCard icon={<Leaf className="h-5 w-5" />} title="生活建议" content={lifestyleAdvice || "生活建议待接入。"} tone="emerald" />
        </div>
      </section>
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
