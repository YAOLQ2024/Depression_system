import { useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import {
  Check,
  Clock,
  FileText,
  Flower2,
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
    stripe: "from-[#c8abea] via-[#a988d3] to-[#e7b7ca]",
    badge: "text-[#7d60ab]",
    badgeBg: "bg-[#f6f0fb]/85",
    badgeBorder: "border-[#dfcdef]",
  },
  sds: {
    stripe: "from-[#b6afe8] via-[#998bd0] to-[#d6b1d6]",
    badge: "text-[#6d65a7]",
    badgeBg: "bg-[#f1f0fc]/85",
    badgeBorder: "border-[#d7d2ef]",
  },
  sas: {
    stripe: "from-[#e8b8c2] via-[#c88ca9] to-[#a985c5]",
    badge: "text-[#ad6f85]",
    badgeBg: "bg-[#fff3f5]/85",
    badgeBorder: "border-[#f2d3db]",
  },
  "social-function": {
    stripe: "from-[#b9d7cf] via-[#86b4a9] to-[#baa3d0]",
    badge: "text-[#568b82]",
    badgeBg: "bg-[#eff8f5]/85",
    badgeBorder: "border-[#cce7df]",
  },
};

function getFallbackRedirectPath(hasConsultation: boolean, homeEntryPath: string) {
  return hasConsultation ? APP_PATHS.consultation : homeEntryPath;
}

function HealingBackgroundDecor() {
  return (
    <>
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background: [
            "radial-gradient(ellipse 62% 52% at 12% 6%, rgba(224, 202, 242, 0.72) 0%, transparent 68%)",
            "radial-gradient(ellipse 56% 52% at 88% 92%, rgba(252, 216, 223, 0.68) 0%, transparent 68%)",
            "radial-gradient(ellipse 46% 40% at 52% 44%, rgba(232, 220, 245, 0.54) 0%, transparent 72%)",
            "linear-gradient(135deg, #f6eff5 0%, #f5f0f8 42%, #fbf0ed 100%)",
          ].join(", "),
        }}
      />
      <div className="pointer-events-none fixed -left-28 top-24 z-0 h-[430px] w-[430px] opacity-55">
        <svg viewBox="0 0 430 430" className="h-full w-full" fill="none" aria-hidden="true">
          <path d="M18 182C80 62 214 25 354 70c-54 27-98 73-128 133-44 87-120 119-208 90Z" fill="rgba(234,214,243,0.40)" />
          <path d="M0 257C87 170 212 168 330 249c-71 1-137 27-190 76C84 369 32 347 0 257Z" fill="rgba(222,203,240,0.34)" />
          <path d="M31 183C124 85 225 89 354 70M1 257c104-55 215-56 329-8M54 104c43 62 70 129 83 221" stroke="rgba(255,255,255,0.72)" strokeWidth="1.25" />
          <path d="M44 236c55-45 117-74 200-84M85 320c21-70 55-132 117-190" stroke="rgba(184,146,207,0.22)" strokeWidth="1" />
        </svg>
      </div>
      <div className="pointer-events-none fixed -right-20 -top-16 z-0 h-[340px] w-[560px] opacity-55">
        <svg viewBox="0 0 560 340" className="h-full w-full" fill="none" aria-hidden="true">
          <path d="M118 4c67 83 167 98 307 53 44-14 88-14 127 0" stroke="rgba(255,255,255,0.88)" strokeWidth="1.4" />
          <path d="M72 35c82 114 219 134 386 74 37-13 70-15 102-4" stroke="rgba(195,162,220,0.32)" strokeWidth="1" />
          <path d="M196 0c42 107 139 163 273 159" stroke="rgba(255,255,255,0.70)" strokeWidth="1" />
          <circle cx="434" cy="137" r="3" fill="rgba(255,255,255,0.84)" />
          <circle cx="488" cy="185" r="2" fill="rgba(188,151,215,0.48)" />
        </svg>
      </div>
      <div className="pointer-events-none fixed -bottom-28 right-0 z-0 h-[330px] w-[420px] opacity-45">
        <svg viewBox="0 0 420 330" className="h-full w-full" fill="none" aria-hidden="true">
          <path d="M204 330c-5-124 43-214 144-270 12 89-21 170-103 243-16 14-29 23-41 27Z" fill="rgba(244,204,217,0.48)" />
          <path d="M286 330c-43-88-42-171 7-249 44 71 45 142 7 218-4 9-9 19-14 31Z" fill="rgba(229,211,243,0.52)" />
          <path d="M204 330c21-110 68-201 144-270M286 330c-8-90-5-174 7-249" stroke="rgba(255,255,255,0.76)" strokeWidth="1.2" />
        </svg>
      </div>
      <div className="pointer-events-none fixed left-[17%] top-[23%] z-0 h-52 w-52 rounded-full bg-[#e7d4f5]/28 blur-3xl" />
      <div className="pointer-events-none fixed bottom-[13%] right-[19%] z-0 h-44 w-44 rounded-full bg-[#ffdbe0]/32 blur-3xl" />
    </>
  );
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
    <div className="scale-selection-page flex h-screen w-full flex-col overflow-hidden bg-[#f6eff5] font-sans text-slate-700">
      <HealingBackgroundDecor />

      {/* ── Header ── */}
      <div className="relative z-10">
        <Header theme="light" title="量表选择" />
      </div>

      {/* ── Main content ── */}
      <main className="relative z-10 flex-1 overflow-y-auto">
        <div className="scale-selection-content mx-auto max-w-[1200px] px-6 py-8 pb-16">
          {/* ── Page header ── */}
          <div className="scale-selection-heading mb-10 text-center">
            {/* Step badge */}
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/80 bg-white/54 px-4 py-1.5 text-xs font-semibold tracking-[0.16em] text-[#8566a9] shadow-[0_5px_18px_rgba(136,103,166,0.12)] backdrop-blur-xl">
              <Flower2 className="h-3.5 w-3.5 text-[#c598bd]" />
              量表阶段
            </div>

            {/* Calligraphy heading */}
            <h1
              className="mb-3 text-4xl leading-snug tracking-wide sm:text-[42px]"
              style={{
                fontFamily: "'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif",
                fontWeight: 400,
                background: "linear-gradient(115deg, #7656a1 0%, #9670bf 48%, #c184a8 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              请选择本次需要完成的量表
            </h1>

            <p className="mx-auto w-fit max-w-none whitespace-nowrap text-[15px] leading-7 text-[#7f748b]">
              支持单选或多选，系统会按固定顺序依次进入所选量表。至少选择 1 份后才能开始评估。
            </p>
          </div>

          {/* ── Content grid ── */}
          <div className="scale-selection-grid grid items-start gap-6 lg:grid-cols-[1fr_320px]">
            {/* ── Scale cards ── */}
            <div className="scale-selection-cards flex flex-col gap-3">
              {!catalogItems.length ? (
                <div className="flex min-h-[20rem] items-center justify-center rounded-3xl border border-dashed border-[#d7c6df] bg-white/48 backdrop-blur-xl">
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
                      aria-pressed={isSelected}
                      onClick={() => toggleScale(item.slug)}
                      className={cn(
                        "scale-selection-card group relative flex items-center gap-5 rounded-2xl border-[1.5px] px-6 py-5 text-left transition-all duration-200",
                        "bg-white/[0.62] backdrop-blur-2xl",
                        "outline-none focus-visible:ring-2 focus-visible:ring-[#b48bd1]/55",
                        isSelected
                          ? "border-[#cba6e0]/80 bg-[linear-gradient(112deg,rgba(255,255,255,0.80),rgba(246,234,252,0.72),rgba(255,238,245,0.70))] shadow-[0_10px_30px_rgba(153,109,184,0.18),inset_0_1px_0_rgba(255,255,255,0.88)]"
                          : "border-white/80 shadow-[0_8px_24px_rgba(121,91,147,0.08),inset_0_1px_0_rgba(255,255,255,0.78)] hover:-translate-y-0.5 hover:border-[#e1cae7] hover:bg-white/[0.76] hover:shadow-[0_13px_28px_rgba(121,91,147,0.13)]",
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
                          "scale-selection-checkbox flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border-2 transition-all duration-200",
                          isSelected
                            ? "scale-105 border-transparent bg-gradient-to-br from-[#a57bd0] to-[#c387aa] shadow-[0_4px_12px_rgba(160,114,189,0.32)]"
                            : "border-[#cfc6da] bg-white/72 group-hover:border-[#b99ccd]",
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
                      <div className="scale-selection-card-body min-w-0 flex-1">
                        <div className="mb-2 flex items-start justify-between gap-3">
                          <span className="text-[17px] font-semibold tracking-tight text-[#42364f]">
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

                        <p className="mb-3 text-[13.5px] leading-relaxed text-[#766b7f]">
                          {item.description}
                        </p>

                        <div className="flex flex-wrap gap-2">
                          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/85 bg-white/58 px-3 py-1 text-xs text-[#71667b]">
                            <FileText className="h-3 w-3 text-[#ad86c9]" />
                            {item.item_count} 题
                          </span>
                          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/85 bg-white/58 px-3 py-1 text-xs text-[#71667b]">
                            <Clock className="h-3 w-3 text-[#d29a83]" />
                            {item.estimatedDurationText}
                          </span>
                          {item.timeframe ? (
                            <span className="inline-flex items-center rounded-full border border-white/85 bg-white/58 px-3 py-1 text-xs text-[#776d80]">
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
            <div className="scale-selection-sidebar sticky top-4 flex flex-col gap-3.5">
              {/* Selection summary */}
              <div className="scale-selection-section rounded-3xl border border-white/80 bg-white/[0.58] p-5 shadow-[0_10px_28px_rgba(121,91,147,0.10),inset_0_1px_0_rgba(255,255,255,0.82)] backdrop-blur-2xl">
                <div className="mb-3 flex items-center gap-2 text-xs font-semibold tracking-[0.13em] text-[#896bab]">
                  <Flower2 className="h-3.5 w-3.5 text-[#c899bb]" />
                  当前选择
                </div>

                <div className="mb-5 flex items-end gap-3">
                  <span className="text-[46px] font-bold leading-none tracking-tight text-[#49375b]">
                    {selectedCount}
                  </span>
                  <span className="pb-1.5 text-sm text-[#7e7286]">已勾选量表</span>
                </div>

                <div className="flex min-h-[48px] flex-col gap-2">
                  {selectedCount ? (
                    selectedScales.map((slug) => {
                      const item = catalogItems.find((c) => c.slug === slug);
                      if (!item) return null;
                      return (
                        <div
                          key={slug}
                          className="flex items-center justify-between rounded-xl border border-[#dfcbea] bg-[#f8f1fa]/72 px-3.5 py-2.5 text-sm shadow-[inset_0_1px_0_rgba(255,255,255,0.65)] animate-fade-slide-in"
                        >
                          <span className="font-medium text-[#5b496b]">
                            {item.short_name || item.name}
                          </span>
                          <span className="text-xs text-[#95889b]">
                            {item.estimatedDurationText}
                          </span>
                        </div>
                      );
                    })
                  ) : (
                    <div className="rounded-xl border border-dashed border-[#d6c7dd] bg-white/35 px-4 py-5 text-center text-sm leading-6 text-[#918498]">
                      还没有选择量表。
                      <br />
                      请勾选至少 1 份量表后再开始。
                    </div>
                  )}
                </div>
              </div>

              {/* Rules */}
              <div className="scale-selection-section rounded-3xl border border-white/80 bg-white/[0.58] p-5 shadow-[0_10px_28px_rgba(121,91,147,0.10),inset_0_1px_0_rgba(255,255,255,0.82)] backdrop-blur-2xl">
                <div className="mb-3 flex items-center gap-2 text-xs font-semibold tracking-[0.13em] text-[#896bab]">
                  <Flower2 className="h-3.5 w-3.5 text-[#c899bb]" />
                  规则说明
                </div>
                <ul className="flex flex-col gap-2.5">
                  {[
                    "支持单选或多选，至少需要选择 1 份量表。",
                    "系统会按固定顺序依次进入所选量表，不按点击顺序调整。",
                    "一旦正式创建量表会话，后续只能继续作答，不能回到这里重选。",
                  ].map((text, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-[13px] leading-6 text-[#766b7f]">
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#f2eaf7]">
                        <Check className="h-2.5 w-2.5 text-[#9b76bd]" strokeWidth={3} />
                      </span>
                      {text}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Error message */}
              {startSelectionError || state.error ? (
                <div className="rounded-2xl border border-rose-200/80 bg-rose-50/80 px-4 py-3 text-sm text-rose-600">
                  {startSelectionError || state.error}
                </div>
              ) : null}

              {/* Start button */}
              <button
                type="button"
                onClick={handleStartSelection}
                disabled={!canStartAssessment}
                className={cn(
                  "scale-selection-start flex w-full items-center justify-center gap-2.5 rounded-full px-6 py-4 text-[15px] font-semibold transition-all duration-200 outline-none",
                  canStartAssessment
                    ? "bg-[linear-gradient(110deg,#8f72c7_0%,#aa79c9_48%,#c98ead_100%)] text-white shadow-[0_12px_26px_rgba(148,101,178,0.26),inset_0_1px_0_rgba(255,255,255,0.34)] hover:-translate-y-0.5 hover:brightness-[1.04] hover:shadow-[0_16px_32px_rgba(148,101,178,0.32)] active:translate-y-0 active:scale-[0.98]"
                    : "cursor-not-allowed border border-white/70 bg-white/45 text-[#a096a6]",
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
              <p className="text-center text-xs text-[#95899b]">
                选中的量表会在下一页按固定顺序逐份播放和作答。
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="scale-selection-footer mt-12 border-t border-white/70 pt-6 text-center text-xs text-[#9a8ea0]">
            量表选择 · 情绪识别数字人辅助评估系统
          </div>
        </div>
      </main>
    </div>
  );
}
