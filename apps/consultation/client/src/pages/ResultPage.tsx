import { startTransition, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Pill, RefreshCw } from "lucide-react";
import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { FlowCompletionState } from "../components/FlowCompletionState";
import {
  buildTrendPointsFromHistory,
  buildResultPageViewModel,
  ConsultationSummaryDrawer,
  DetailDrawer,
  DigitalCounselor,
  SummaryDashboard,
} from "../features/result-page";
import { ConsultationLayout } from "../layouts";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";
import { getAssessmentScaleDetail } from "../services/api/assessment.api";
import { getEncounterScaleHistory } from "../services/api/consultation.api";
import type { ResultTrendPoint } from "../features/result-page";
import type { AssessmentScaleDetail } from "../types";

type ActiveDrawerState =
  | { kind: "scale"; scaleId: string }
  | { kind: "consultation" }
  | null;

export default function ResultPage() {
  const navigate = useNavigate();
  const { state, actions } = useConsultationAppContext();
  const [activeDrawer, setActiveDrawer] = useState<ActiveDrawerState>(null);
  const [assessmentScaleDetails, setAssessmentScaleDetails] = useState<Record<string, AssessmentScaleDetail>>({});
  const [assessmentScaleHistories, setAssessmentScaleHistories] = useState<Record<string, ResultTrendPoint[]>>({});
  const [scaleDetailLoadErrors, setScaleDetailLoadErrors] = useState<Record<string, string>>({});
  const gradientActionButtonClass =
    "flex flex-1 items-center justify-center gap-2 rounded-full bg-[linear-gradient(120deg,rgba(96,165,250,0.95),rgba(99,102,241,0.98),rgba(168,85,247,0.95),rgba(96,165,250,0.95))] px-6 py-3.5 font-medium text-white shadow-[0_18px_50px_rgba(99,102,241,0.28)] transition-all hover:scale-[1.02] hover:brightness-110 active:scale-[0.98]";
  const secondaryActionButtonClass =
    "flex flex-1 items-center justify-center gap-2 rounded-full border border-white/26 bg-white/[0.06] px-6 py-3.5 font-medium text-white transition-all hover:scale-[1.02] hover:bg-white/[0.12] active:scale-[0.98]";

  const completedScaleIds = useMemo(() => {
    const slugs = (state.assessment?.results || []).map((result) => result.scale_slug);
    return slugs.filter((slug, index) => Boolean(slug) && slugs.indexOf(slug) === index);
  }, [state.assessment]);

  useEffect(() => {
    const sessionId = state.assessment?.session_id || null;
    if (!sessionId || !completedScaleIds.length) {
      setAssessmentScaleDetails({});
      setScaleDetailLoadErrors({});
      return;
    }

    let cancelled = false;
    setAssessmentScaleDetails({});
    setScaleDetailLoadErrors({});

    void (async () => {
      const settled = await Promise.allSettled(
        completedScaleIds.map(async (scaleSlug) => ({
          scaleSlug,
          detail: await getAssessmentScaleDetail(sessionId, scaleSlug),
        })),
      );

      if (cancelled) {
        return;
      }

      const nextDetails: Record<string, AssessmentScaleDetail> = {};
      const nextErrors: Record<string, string> = {};

      settled.forEach((result, index) => {
        const scaleSlug = completedScaleIds[index];
        if (result.status === "fulfilled") {
          nextDetails[scaleSlug] = result.value.detail;
          return;
        }

        nextErrors[scaleSlug] =
          result.reason instanceof Error ? result.reason.message : "详细作答加载失败，请稍后重试。";
      });

      setAssessmentScaleDetails(nextDetails);
      setScaleDetailLoadErrors(nextErrors);
    })();

    return () => {
      cancelled = true;
    };
  }, [completedScaleIds, state.assessment?.session_id]);

  useEffect(() => {
    if (!completedScaleIds.length) {
      setAssessmentScaleHistories({});
      return;
    }

    let cancelled = false;
    setAssessmentScaleHistories({});

    void (async () => {
      const settled = await Promise.allSettled(
        completedScaleIds.map(async (scaleSlug) => ({
          scaleSlug,
          history: await getEncounterScaleHistory(scaleSlug),
        })),
      );

      if (cancelled) {
        return;
      }

      const nextHistories: Record<string, ResultTrendPoint[]> = {};
      settled.forEach((result, index) => {
        const scaleSlug = completedScaleIds[index];
        if (result.status !== "fulfilled") {
          return;
        }
        nextHistories[scaleSlug] = buildTrendPointsFromHistory(result.value.history.history);
      });

      setAssessmentScaleHistories(nextHistories);
    })();

    return () => {
      cancelled = true;
    };
  }, [completedScaleIds]);

  const viewModel = useMemo(
    () =>
      buildResultPageViewModel({
        assessment: state.assessment,
        assessmentCatalog: state.assessmentCatalog,
        assessmentScaleDetails,
        consultation: state.consultation,
      }),
    [assessmentScaleDetails, state.assessment, state.assessmentCatalog, state.consultation],
  );

  const canRenderResult = state.assessment?.status === "completed" && viewModel.hasAssessment;
  const isDrawerOpen = activeDrawer !== null;
  const selectedScaleId = activeDrawer?.kind === "scale" ? activeDrawer.scaleId : null;
  const counselorPaneWidth = "clamp(420px, 28vw, 580px)";
  const selectedScaleDetail = useMemo(() => {
    if (!selectedScaleId) {
      return null;
    }

    const detail = viewModel.scaleDetails[selectedScaleId] || null;
    if (!detail) {
      return null;
    }

    const nextDetail = {
      ...detail,
      history: assessmentScaleHistories[selectedScaleId] || [],
    };
    const loadError = scaleDetailLoadErrors[selectedScaleId];
    if (!loadError) {
      return nextDetail;
    }

    return {
      ...nextDetail,
      itemResultsReady: false,
      itemResultsNotice: loadError,
    };
  }, [assessmentScaleHistories, scaleDetailLoadErrors, selectedScaleId, viewModel.scaleDetails]);
  const selectedDrawerWidth = "calc((100% - 5px) / 2)";

  const modules = viewModel.modules.map((module) =>
    module.id === "consultation-summary" && viewModel.consultationSummary
      ? {
          ...module,
          actionLabel: "查看详情",
          onAction: () => {
            setActiveDrawer({ kind: "consultation" });
          },
        }
      : module,
  );

  const handleOpenScaleDetail = (scaleId: string) => {
    setActiveDrawer({ kind: "scale", scaleId });
  };

  const handleCloseDrawer = () => {
    setActiveDrawer(null);
  };

  const handleOpenPrimaryScaleDetail = () => {
    const scaleId = selectedScaleId || viewModel.defaultScaleId;
    if (!scaleId) {
      return;
    }

    setActiveDrawer({ kind: "scale", scaleId });
  };

  const handleStartNewConsultation = async () => {
    const started = await actions.handleStartConsultation();
    if (!started) {
      return;
    }

    startTransition(() => {
      navigate(APP_PATHS.consultation, { state: { sessionId: started.session_id } });
    });
  };

  const handleOpenAvailableFlow = async () => {
    if (state.homeEntryPath === APP_PATHS.consultation && !state.consultation && !state.assessment) {
      await handleStartNewConsultation();
      return;
    }

    navigate(state.homeEntryPath);
  };

  const desktopDrawerContent =
    activeDrawer?.kind === "consultation" ? (
      <ConsultationSummaryDrawer
        open
        summary={viewModel.consultationSummary}
        onClose={handleCloseDrawer}
      />
    ) : (
      <DetailDrawer open detail={selectedScaleDetail} onClose={handleCloseDrawer} />
    );

  return (
    <ConsultationLayout backgroundImage="/4K.png" title="评估结果">
      <div className="relative h-full w-full overflow-hidden p-4 md:p-6 lg:p-8">
        {!canRenderResult ? (
          <FlowCompletionState
            title="尚未生成评估结果"
            description={
              state.assessment
                ? "当前量表流程尚未完成，先回到主流程继续完成评估。"
                : "当前还没有可展示的结果页数据，先进入问诊主流程生成本轮结果。"
            }
            actionLabel={state.homeEntryLabel}
            onAction={handleOpenAvailableFlow}
          />
      ) : (
          <>
            <div className="flex h-full gap-3 lg:gap-[5px]">
              <div
                className="hidden shrink-0 transition-all duration-[800ms] ease-[cubic-bezier(0.2,0.1,0.15,1)] xl:block"
                style={{
                  width: isDrawerOpen ? 0 : counselorPaneWidth,
                  opacity: isDrawerOpen ? 0 : 1,
                  marginRight: isDrawerOpen ? "-5px" : 0,
                  transform: isDrawerOpen ? "translateX(-32px)" : "translateX(0)",
                  pointerEvents: isDrawerOpen ? "none" : "auto",
                }}
              >
                <div className="h-full w-full">
                  <DigitalCounselor className="px-0" overallSeverity={viewModel.overallSeverity} />
                </div>
              </div>

              <div className="min-w-0 flex-1 transition-all duration-[800ms] ease-[cubic-bezier(0.2,0.1,0.15,1)]">
                <div className="relative h-full overflow-hidden rounded-[10px] border border-white/16 bg-[linear-gradient(180deg,rgba(8,16,32,0.74),rgba(8,16,32,0.52))] shadow-[0_24px_60px_rgba(15,23,42,0.26)] backdrop-blur-[20px]">
                  <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),transparent_18%,transparent_82%,rgba(255,255,255,0.03))]" />
                  <div className="relative z-10 flex h-full min-h-0 flex-col p-4 md:p-5">
                    <div className="min-h-0 flex-1 overflow-y-auto pr-1">
                      <SummaryDashboard
                        modules={modules}
                        overallScore={viewModel.overallScore}
                        overallSeverity={viewModel.overallSeverity}
                        overallRiskLevel={viewModel.overallRiskLevel}
                        overallRiskReason={viewModel.overallRiskReason}
                        scales={viewModel.scales}
                        selectedScaleId={selectedScaleId}
                        onOpenScaleDetail={handleOpenScaleDetail}
                        clinicalAdvice={viewModel.clinicalAdvice}
                        lifestyleAdvice={viewModel.lifestyleAdvice}
                        compact={isDrawerOpen}
                      />
                    </div>

                    <div className="mt-4 flex flex-col gap-3 border-t border-white/16 pt-4 sm:flex-row">
                      <button
                        onClick={handleOpenPrimaryScaleDetail}
                        disabled={!viewModel.defaultScaleId}
                        className={cn(
                          gradientActionButtonClass,
                          viewModel.defaultScaleId
                            ? ""
                            : "cursor-not-allowed bg-slate-300/25 text-white/55 shadow-none hover:scale-100 hover:brightness-100",
                        )}
                      >
                        <FileText className="h-5 w-5" />
                        查看量表详情
                      </button>

                      <button
                        onClick={() =>
                          navigate(APP_PATHS.intervention, {
                            state: {
                              source: "workflow_result",
                              bindConsultation: true,
                              consultationSessionId: state.consultation?.session_id ?? null,
                              encounterSessionId:
                                state.assessment?.encounter_session_id ||
                                state.consultation?.encounter_session_id ||
                                null,
                              assessmentSessionId: state.assessment?.session_id ?? null,
                            },
                          })
                        }
                        className={gradientActionButtonClass}
                      >
                        <Pill className="h-5 w-5" />
                        进入调节干预
                      </button>

                      <button
                        onClick={handleStartNewConsultation}
                        disabled={state.loading}
                        className={cn(
                          secondaryActionButtonClass,
                          state.loading && "cursor-wait opacity-70",
                        )}
                      >
                        <RefreshCw className={cn("h-5 w-5", state.loading && "animate-spin")} />
                        新开完整问诊
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div
                className="relative hidden shrink-0 transition-all duration-[800ms] ease-[cubic-bezier(0.2,0.1,0.15,1)] lg:block"
                style={{
                  width: isDrawerOpen ? selectedDrawerWidth : 0,
                  opacity: isDrawerOpen ? 1 : 0,
                  marginLeft: isDrawerOpen ? 0 : "-5px",
                  transform: isDrawerOpen ? "translateX(0)" : "translateX(32px)",
                  pointerEvents: isDrawerOpen ? "auto" : "none",
                }}
              >
                <div className="h-full w-full">
                  {desktopDrawerContent}
                </div>
              </div>
            </div>

            {isDrawerOpen ? (
              <>
                <button
                  type="button"
                  aria-label="关闭详情遮罩"
                  onClick={handleCloseDrawer}
                  className="absolute inset-0 z-20 bg-slate-950/35 backdrop-blur-[2px] lg:hidden"
                />
                <div className="absolute inset-3 z-30 lg:hidden">
                  {activeDrawer?.kind === "consultation" ? (
                    <ConsultationSummaryDrawer
                      open
                      summary={viewModel.consultationSummary}
                      onClose={handleCloseDrawer}
                    />
                  ) : (
                    <DetailDrawer open detail={selectedScaleDetail} onClose={handleCloseDrawer} />
                  )}
                </div>
              </>
            ) : null}
          </>
        )}
      </div>
    </ConsultationLayout>
  );
}
