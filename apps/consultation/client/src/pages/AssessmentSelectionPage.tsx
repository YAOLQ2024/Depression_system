import { useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import {
  Check,
  Clock,
  FileText,
  LoaderCircle,
  Play,
} from "lucide-react";

import { useConsultationAppContext } from "../app/ConsultationAppContext";
import {
  buildAssessmentSelectionCatalog,
  normalizeSelectedScaleOrder,
  type ActiveScaleSelectionSlug,
} from "../features/assessment-selection/scaleSelectionMeta";
import { Header } from "../components/Header";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";

/** Per-slug accent color mapping */
const SLUG_ACCENT: Record<
  ActiveScaleSelectionSlug,
  { stripe: string; badge: string; badgeBg: string; badgeBorder: string }
> = {
  phq9: {
    stripe: "from-purple-400 to-violet-600",
    badge: "text-violet-600",
    badgeBg: "bg-violet-50",
    badgeBorder: "border-violet-200",
  },
  sds: {
    stripe: "from-sky-400 to-blue-600",
    badge: "text-blue-600",
    badgeBg: "bg-blue-50",
    badgeBorder: "border-blue-200",
  },
  sas: {
    stripe: "from-amber-400 to-orange-500",
    badge: "text-orange-600",
    badgeBg: "bg-orange-50",
    badgeBorder: "border-orange-200",
  },
  "social-function": {
    stripe: "from-emerald-400 to-teal-600",
    badge: "text-teal-600",
    badgeBg: "bg-teal-50",
    badgeBorder: "border-teal-200",
  },
};

function getFallbackRedirectPath(hasConsultation: boolean, homeEntryPath: string) {
  return hasConsultation ? APP_PATHS.consultation : homeEntryPath;
}

export default function AssessmentSelectionPage() {
  const navigate = useNavigate();
  const { state, actions } = useConsultationAppContext();
  const [selectedScales, setSelectedScales] = useState<ActiveScaleSelectionSlug[]>([]);
  const [isStartingSelection, setIsStartingSelection] = useState(false);
  const [startSelectionError, setStartSelectionError] = useState("");

  useEffect(() => {
    actions.resetFeedback();
    setStartSelectionError("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const catalogItems = useMemo(
    () => buildAssessmentSelectionCatalog(state.assessmentCatalog),
    [state.assessmentCatalog],
  );
  const selectedCount = selectedScales.length;
  const isCreatingAssessment = state.loading || isStartingSelection;
  const canStartAssessment = selectedCount > 0 && !isCreatingAssessment;
  const consultationStatus = state.consultation?.status || null;
  const hasActiveAssessment = Boolean(state.assessment && state.assessment.status !== "completed");
  const fallbackRedirectPath = getFallbackRedirectPath(Boolean(state.consultation), state.homeEntryPath);

  // ── Guards ──
  if (state.assessment?.status === "completed") {
    return <Navigate to={APP_PATHS.result} replace />;
  }
  if (hasActiveAssessment && !isStartingSelection) {
    return <Navigate to={APP_PATHS.assessment} replace />;
  }
  if (consultationStatus === "paused_for_human_review") {
    return <Navigate to={APP_PATHS.consultation} replace />;
  }
  if (consultationStatus !== "handoff_ready") {
    return <Navigate to={fallbackRedirectPath} replace />;
  }

  // ── Handlers ──
  function toggleScale(slug: ActiveScaleSelectionSlug) {
    setSelectedScales((current) => {
      if (current.includes(slug)) {
        return current.filter((item) => item !== slug);
      }
      return normalizeSelectedScaleOrder([...current, slug]);
    });
  }

  async function handleStartSelection() {
    if (!canStartAssessment) return;

    setStartSelectionError("");
    setIsStartingSelection(true);

    let navigatedToAssessment = false;

    try {
      const createdAssessment = await actions.handleStartAssessment(selectedScales);
      if (!createdAssessment) return;

      navigatedToAssessment = true;
      navigate(APP_PATHS.assessment, {
        replace: true,
        state: { sessionId: createdAssessment.session_id },
      });
    } catch (caught) {
      setStartSelectionError(
        caught instanceof Error ? caught.message : "进入量表页失败，请重试。",
      );
    } finally {
      if (!navigatedToAssessment) {
        setIsStartingSelection(false);
      }
    }
  }

  function handleGoBack() {
    navigate(fallbackRedirectPath);
  }

  // ── Render ──
  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-[#f8f6f3] font-sans">
      {/* ── Warm light background ambience ── */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background: [
            "radial-gradient(ellipse 70% 50% at 15% 5%, rgba(180,154,255,0.10) 0%, transparent 60%)",
            "radial-gradient(ellipse 50% 40% at 85% 90%, rgba(255,200,120,0.08) 0%, transparent 50%)",
            "radial-gradient(ellipse 40% 40% at 50% 40%, rgba(109,213,160,0.04) 0%, transparent 40%)",
          ].join(", "),
        }}
      />

      {/* ── Header ── */}
      <div className="relative z-10">
        <Header theme="light" title="量表选择" />
      </div>

      {/* ── Main content ── */}
      <main className="relative z-10 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1200px] px-6 py-8 pb-16">
          {/* ── Page header ── */}
          <div className="mb-10 text-center">
            {/* Step badge */}
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-4 py-1.5 text-xs font-semibold tracking-widest text-violet-600 uppercase">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-500" />
              量表阶段
            </div>

            {/* Calligraphy heading */}
            <h1
              className="mb-3 text-4xl leading-snug tracking-wide sm:text-[42px]"
              style={{
                fontFamily: "'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif",
                fontWeight: 400,
                background: "linear-gradient(135deg, #7c5ce7 0%, #9070f0 40%, #ffa726 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              请选择本次需要完成的量表
            </h1>

            <p className="mx-auto w-fit max-w-none whitespace-nowrap text-[15px] leading-7 text-slate-500">
              支持单选或多选，系统会按固定顺序依次进入所选量表。至少选择 1 份后才能开始评估。
            </p>
          </div>

          {/* ── Content grid ── */}
          <div className="grid items-start gap-6 lg:grid-cols-[1fr_320px]">
            {/* ── Scale cards ── */}
            <div className="flex flex-col gap-3">
              {!catalogItems.length ? (
                <div className="flex min-h-[20rem] items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-white/60">
                  <div className="text-center">
                    <LoaderCircle className="mx-auto h-8 w-8 animate-spin text-violet-400" />
                    <p className="mt-3 text-sm text-slate-500">正在加载量表目录...</p>
                  </div>
                </div>
              ) : (
                catalogItems.map((item) => {
                  const isSelected = selectedScales.includes(item.slug);
                  const accent = SLUG_ACCENT[item.slug];

                  return (
                    <button
                      key={item.slug}
                      type="button"
                      onClick={() => toggleScale(item.slug)}
                      className={cn(
                        "group relative flex items-center gap-5 rounded-2xl border-[1.5px] px-6 py-5 text-left transition-all duration-200",
                        "bg-white/85 backdrop-blur-sm",
                        "outline-none focus-visible:ring-2 focus-visible:ring-violet-300/50",
                        isSelected
                          ? "border-violet-300/60 bg-violet-50/40 shadow-[0_4px_20px_rgba(124,92,231,0.12)]"
                          : "border-slate-200/60 shadow-[0_2px_12px_rgba(100,70,160,0.05)] hover:border-slate-300 hover:bg-white hover:shadow-[0_4px_20px_rgba(100,70,160,0.09)]",
                      )}
                    >
                      {/* Accent stripe */}
                      <div
                        className={cn(
                          "absolute left-0 top-4 bottom-4 w-[3px] rounded-r-full bg-gradient-to-b transition-opacity",
                          accent.stripe,
                          isSelected ? "opacity-100" : "opacity-0",
                        )}
                      />

                      {/* Checkbox */}
                      <div
                        className={cn(
                          "flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border-2 transition-all duration-200",
                          isSelected
                            ? "scale-105 border-transparent bg-gradient-to-br from-violet-500 to-purple-600"
                            : "border-slate-300 bg-white group-hover:border-slate-400",
                        )}
                      >
                        <Check
                          className={cn(
                            "h-3.5 w-3.5 text-white transition-all duration-200",
                            isSelected ? "scale-100 opacity-100" : "scale-50 opacity-0",
                          )}
                          strokeWidth={3}
                        />
                      </div>

                      {/* Card body */}
                      <div className="min-w-0 flex-1">
                        <div className="mb-2 flex items-start justify-between gap-3">
                          <span className="text-[17px] font-semibold tracking-tight text-slate-800">
                            {item.short_name || item.name}
                          </span>
                          <span
                            className={cn(
                              "shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide",
                              accent.badge,
                              accent.badgeBg,
                              accent.badgeBorder,
                            )}
                          >
                            {item.name}
                          </span>
                        </div>

                        <p className="mb-3 text-[13.5px] leading-relaxed text-slate-500">
                          {item.description}
                        </p>

                        <div className="flex flex-wrap gap-2">
                          <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600">
                            <FileText className="h-3 w-3 text-violet-400" />
                            {item.item_count} 题
                          </span>
                          <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600">
                            <Clock className="h-3 w-3 text-amber-500" />
                            {item.estimatedDurationText}
                          </span>
                          {item.timeframe ? (
                            <span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-500">
                              {item.timeframe}
                            </span>
                          ) : null}
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>

            {/* ── Sidebar ── */}
            <div className="sticky top-4 flex flex-col gap-3.5">
              {/* Selection summary */}
              <div className="rounded-3xl border border-slate-200/60 bg-white/90 p-5 shadow-[0_2px_12px_rgba(100,70,160,0.05)] backdrop-blur-sm">
                <div className="mb-3 text-xs font-semibold tracking-widest text-violet-500 uppercase">
                  当前选择
                </div>

                <div className="mb-5 flex items-end gap-3">
                  <span className="text-[46px] font-bold leading-none tracking-tight text-slate-800">
                    {selectedCount}
                  </span>
                  <span className="pb-1.5 text-sm text-slate-500">已勾选量表</span>
                </div>

                <div className="flex min-h-[48px] flex-col gap-2">
                  {selectedCount ? (
                    selectedScales.map((slug) => {
                      const item = catalogItems.find((c) => c.slug === slug);
                      if (!item) return null;
                      return (
                        <div
                          key={slug}
                          className="flex items-center justify-between rounded-xl border border-violet-200/60 bg-violet-50/50 px-3.5 py-2.5 text-sm animate-fade-slide-in"
                        >
                          <span className="font-medium text-slate-700">
                            {item.short_name || item.name}
                          </span>
                          <span className="text-xs text-slate-400">
                            {item.estimatedDurationText}
                          </span>
                        </div>
                      );
                    })
                  ) : (
                    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 px-4 py-5 text-center text-sm leading-6 text-slate-400">
                      还没有选择量表。
                      <br />
                      请勾选至少 1 份量表后再开始。
                    </div>
                  )}
                </div>
              </div>

              {/* Rules */}
              <div className="rounded-3xl border border-slate-200/60 bg-white/90 p-5 shadow-[0_2px_12px_rgba(100,70,160,0.05)] backdrop-blur-sm">
                <div className="mb-3 text-xs font-semibold tracking-widest text-violet-500 uppercase">
                  规则说明
                </div>
                <ul className="flex flex-col gap-2.5">
                  {[
                    "支持单选或多选，至少需要选择 1 份量表。",
                    "系统会按固定顺序依次进入所选量表，不按点击顺序调整。",
                    "一旦正式创建量表会话，后续只能继续作答，不能回到这里重选。",
                  ].map((text, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-[13px] leading-6 text-slate-500">
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-violet-50">
                        <Check className="h-2.5 w-2.5 text-violet-500" strokeWidth={3} />
                      </span>
                      {text}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Error message */}
              {startSelectionError || state.error ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
                  {startSelectionError || state.error}
                </div>
              ) : null}

              {/* Start button */}
              <button
                type="button"
                onClick={handleStartSelection}
                disabled={!canStartAssessment}
                className={cn(
                  "flex w-full items-center justify-center gap-2.5 rounded-full px-6 py-4 text-[15px] font-semibold transition-all duration-200 outline-none",
                  canStartAssessment
                    ? "bg-gradient-to-r from-violet-500 to-purple-600 text-white shadow-[0_4px_20px_rgba(124,92,231,0.30)] hover:-translate-y-0.5 hover:shadow-[0_6px_28px_rgba(124,92,231,0.40)] active:translate-y-0 active:scale-[0.98]"
                    : "cursor-not-allowed bg-slate-200 text-slate-400",
                )}
              >
                {isCreatingAssessment ? (
                  <>
                    <LoaderCircle className="h-5 w-5 animate-spin" />
                    正在创建量表会话...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    开始量表评估
                  </>
                )}
              </button>
              <p className="text-center text-xs text-slate-400">
                选中的量表会在下一页按固定顺序逐份播放和作答。
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="mt-12 border-t border-slate-200/60 pt-6 text-center text-xs text-slate-400">
            量表选择 · 抑郁症数字人辅助评估系统
          </div>
        </div>
      </main>
    </div>
  );
}
