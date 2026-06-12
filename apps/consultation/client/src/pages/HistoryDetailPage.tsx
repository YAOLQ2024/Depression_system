import { useEffect, useMemo, useState } from "react";
import { CalendarClock, ClipboardList, Download, Layers3, MessageSquareText } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { EncounterTimeline } from "../components/EncounterTimeline";
import {
  buildResultPageViewModel,
  ConsultationSummaryDrawer,
  DetailDrawer,
  GlassCard,
  SummaryDashboard,
} from "../features/result-page";
import {
  buildEncounterAssessmentSession,
  buildEncounterConsultationSession,
  buildHistoryInsightItems,
  buildTranscriptPreview,
  getEncounterRiskFrontDisplay,
  getEncounterRiskSummary,
} from "../features/history/adapter";
import { useHistoryDetail } from "../hooks/useHistoryDetail";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";
import { getAssessmentScaleDetail } from "../services/api/assessment.api";
import { downloadEncounterPdf } from "../services/api/consultation.api";
import type { AssessmentScaleDetail } from "../types";

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

type ActiveDrawerState =
  | { kind: "scale"; scaleId: string }
  | { kind: "consultation" }
  | null;

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const candidate = new Date(iso);
  if (Number.isNaN(candidate.getTime())) {
    return iso;
  }
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${candidate.getFullYear()}-${pad(candidate.getMonth() + 1)}-${pad(candidate.getDate())} ${pad(candidate.getHours())}:${pad(candidate.getMinutes())}`;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim();
  return normalized ? normalized : null;
}

function getRiskToneClasses(label: string | null) {
  if (!label) {
    return "border-white/15 bg-white/6 text-slate-200";
  }

  if (label.includes("高") || label.includes("重") || label.includes("危")) {
    return "border-rose-400/35 bg-rose-500/12 text-rose-200";
  }

  if (label.includes("中") || label.includes("关注")) {
    return "border-amber-300/35 bg-amber-400/12 text-amber-100";
  }

  if (label.includes("低") || label.includes("轻") || label.includes("正常")) {
    return "border-emerald-300/35 bg-emerald-400/12 text-emerald-100";
  }

  return "border-primary-300/35 bg-primary-500/12 text-primary-100";
}

function buildMetricCard(label: string, value: string, hint?: string | null) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
      <div className="text-xs font-medium tracking-[0.16em] text-slate-400">{label}</div>
      <div className="mt-2 text-base font-semibold text-white">{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-400">{hint}</div> : null}
    </div>
  );
}

export default function HistoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { state: appState } = useConsultationAppContext();
  const { state, reload } = useHistoryDetail(id);

  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [activeDrawer, setActiveDrawer] = useState<ActiveDrawerState>(null);
  const [assessmentScaleDetails, setAssessmentScaleDetails] = useState<Record<string, AssessmentScaleDetail>>({});
  const [scaleDetailLoadErrors, setScaleDetailLoadErrors] = useState<Record<string, string>>({});

  const encounter = state.encounter;
  const consultationSession = useMemo(
    () => buildEncounterConsultationSession(encounter),
    [encounter],
  );
  const assessmentSession = useMemo(
    () => buildEncounterAssessmentSession(encounter),
    [encounter],
  );
  const riskSummary = useMemo(() => getEncounterRiskSummary(encounter), [encounter]);
  const riskFrontDisplay = useMemo(() => getEncounterRiskFrontDisplay(encounter), [encounter]);

  const completedScaleIds = useMemo(() => {
    const slugs = (assessmentSession?.results || []).map((result) => result.scale_slug);
    return slugs.filter((slug, index) => Boolean(slug) && slugs.indexOf(slug) === index);
  }, [assessmentSession]);

  useEffect(() => {
    const sessionId = assessmentSession?.session_id || null;
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
  }, [assessmentSession?.session_id, completedScaleIds]);

  const viewModel = useMemo(
    () =>
      buildResultPageViewModel({
        assessment: assessmentSession,
        assessmentCatalog: appState.assessmentCatalog,
        assessmentScaleDetails,
        consultation: consultationSession,
      }),
    [appState.assessmentCatalog, assessmentScaleDetails, assessmentSession, consultationSession],
  );

  const selectedScaleId = activeDrawer?.kind === "scale" ? activeDrawer.scaleId : null;
  const selectedScaleDetail = useMemo(() => {
    if (!selectedScaleId) {
      return null;
    }

    const detail = viewModel.scaleDetails[selectedScaleId] || null;
    if (!detail) {
      return null;
    }

    const loadError = scaleDetailLoadErrors[selectedScaleId];
    if (!loadError) {
      return detail;
    }

    return {
      ...detail,
      itemResultsReady: false,
      itemResultsNotice: loadError,
    };
  }, [scaleDetailLoadErrors, selectedScaleId, viewModel.scaleDetails]);

  const modules = useMemo(
    () =>
      viewModel.modules.map((module) =>
        module.id === "consultation-summary" && viewModel.consultationSummary
          ? {
              ...module,
              actionLabel: "查看详情",
              onAction: () => setActiveDrawer({ kind: "consultation" }),
            }
          : module,
      ),
    [viewModel.consultationSummary, viewModel.modules],
  );

  const symptomInsights = useMemo(
    () => buildHistoryInsightItems(consultationSession?.current_history_structured_result),
    [consultationSession?.current_history_structured_result],
  );
  const highRiskInsights = useMemo(
    () => buildHistoryInsightItems(consultationSession?.high_risk_screening_result),
    [consultationSession?.high_risk_screening_result],
  );
  const transcriptPreview = useMemo(
    () => buildTranscriptPreview(consultationSession?.subtitle_history),
    [consultationSession?.subtitle_history],
  );

  const summaryMessage =
    asString(riskFrontDisplay?.message) ||
    consultationSession?.digital_human_consultation_summary ||
    consultationSession?.chief_complaint_stage_summary ||
    encounter?.consultation?.chief_complaint_summary ||
    "本次历史记录已汇总，可查看问诊摘要、量表结果与时间线。";
  const riskLevelLabel =
    asString(riskSummary?.risk_level_label) ||
    asString(riskFrontDisplay?.risk_level_label) ||
    encounter?.assessment_results[0]?.interpretation_label ||
    null;
  const requiredScaleLabels =
    viewModel.consultationSummary?.requiredScaleLabels ||
    [];

  const handleDownloadPdf = async () => {
    if (!id) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      await downloadEncounterPdf(id);
    } catch (err: any) {
      setDownloadError(err?.message || "下载失败");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.16),transparent_24%),linear-gradient(135deg,#020617,#0b1120_52%,#111827)] text-white">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <button
            onClick={() => navigate(APP_PATHS.history)}
            className="text-sm text-slate-400 transition-colors hover:text-white"
          >
            ← 返回历史列表
          </button>

          <div className="flex items-center gap-3">
            {encounter && encounter.status === "completed" ? (
              <button
                onClick={handleDownloadPdf}
                disabled={downloading}
                className="inline-flex items-center gap-2 rounded-full border border-primary-300/30 bg-primary-500/12 px-4 py-2 text-sm font-medium text-primary-100 transition-colors hover:bg-primary-500/20 disabled:cursor-wait disabled:opacity-70"
              >
                <Download className="h-4 w-4" />
                {downloading ? "生成中..." : "下载 PDF 报告"}
              </button>
            ) : null}
          </div>
        </div>

        {state.loading ? (
          <div className="py-20 text-center text-slate-400">加载中...</div>
        ) : null}

        {state.error ? (
          <div className="py-20 text-center">
            <div className="text-sm text-red-300">{state.error}</div>
            <button
              onClick={reload}
              className="mt-3 text-sm text-primary-200 transition-colors hover:text-primary-100"
            >
              重试
            </button>
          </div>
        ) : null}

        {downloadError ? (
          <div className="mb-4 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {downloadError}
          </div>
        ) : null}

        {encounter ? (
          <div className="space-y-4">
            <GlassCard className="overflow-hidden p-5 md:p-6">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                <div className="max-w-3xl">
                  <div className="mb-3 flex flex-wrap gap-2">
                    <span
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs font-medium",
                        encounter.status === "completed"
                          ? "border-emerald-300/35 bg-emerald-400/12 text-emerald-100"
                          : "border-amber-300/35 bg-amber-400/12 text-amber-100",
                      )}
                    >
                      {STATUS_LABELS[encounter.status] || encounter.status}
                    </span>
                    <span className="rounded-full border border-white/12 bg-white/[0.06] px-3 py-1 text-xs font-medium text-slate-200">
                      {FLOW_LABELS[encounter.current_flow_type] || encounter.current_flow_type}
                    </span>
                    {riskLevelLabel ? (
                      <span
                        className={cn(
                          "rounded-full border px-3 py-1 text-xs font-medium",
                          getRiskToneClasses(riskLevelLabel),
                        )}
                      >
                        {riskLevelLabel}
                      </span>
                    ) : null}
                  </div>

                  <div className="text-xs font-medium tracking-[0.22em] text-primary-200/90">
                    ENCOUNTER DETAIL
                  </div>
                  <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">
                    历史就诊详情
                  </h1>
                  <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-200/88">
                    {summaryMessage}
                  </p>

                  {requiredScaleLabels.length ? (
                    <div className="mt-5 flex flex-wrap gap-2">
                      {requiredScaleLabels.map((label) => (
                        <span
                          key={label}
                          className="rounded-full border border-primary-300/25 bg-primary-500/10 px-3 py-1 text-xs font-medium text-primary-100"
                        >
                          {label}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>

                <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2 xl:max-w-[420px]">
                  {buildMetricCard("创建时间", formatDateTime(encounter.created_at))}
                  {buildMetricCard("完成时间", formatDateTime(encounter.completed_at))}
                  {buildMetricCard(
                    "数字医生",
                    consultationSession?.assigned_doctor_persona || "—",
                    consultationSession?.chief_complaint_summary || null,
                  )}
                  {buildMetricCard(
                    "量表数量",
                    String(viewModel.scales.length || encounter.assessment_results.length || 0),
                    riskLevelLabel ? `综合风险：${riskLevelLabel}` : "尚未生成综合风险标签",
                  )}
                </div>
              </div>
            </GlassCard>

            {viewModel.hasAssessment ? (
              <GlassCard className="p-4 md:p-5">
                <SummaryDashboard
                  title="本次综合评估结果"
                  modules={modules}
                  overallScore={viewModel.overallScore}
                  overallSeverity={viewModel.overallSeverity}
                  scales={viewModel.scales}
                  selectedScaleId={selectedScaleId}
                  onOpenScaleDetail={(scaleId) => setActiveDrawer({ kind: "scale", scaleId })}
                  clinicalAdvice={viewModel.clinicalAdvice}
                  lifestyleAdvice={viewModel.lifestyleAdvice}
                />
              </GlassCard>
            ) : (
              <GlassCard className="p-5">
                <div className="flex items-start gap-3">
                  <Layers3 className="mt-0.5 h-5 w-5 text-primary-200" />
                  <div>
                    <h2 className="text-lg font-semibold text-white">量表结果</h2>
                    <p className="mt-2 text-sm leading-7 text-slate-300/88">
                      本次记录尚未形成完整的量表评估结果，当前详情页仍保留问诊摘要、结构化线索和时间线，方便继续回看。
                    </p>
                  </div>
                </div>
              </GlassCard>
            )}

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_360px]">
              <div className="space-y-4">
                {viewModel.consultationSummary ? (
                  <GlassCard className="p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 text-primary-200">
                          <ClipboardList className="h-5 w-5" />
                          <h2 className="text-lg font-semibold text-white">咨询摘要</h2>
                        </div>
                        <p className="mt-3 text-sm leading-7 text-slate-200/88">
                          {viewModel.consultationSummary.overallSummary}
                        </p>
                      </div>
                      <button
                        onClick={() => setActiveDrawer({ kind: "consultation" })}
                        className="shrink-0 rounded-full border border-white/16 bg-white/[0.05] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-white/[0.1]"
                      >
                        查看完整摘要
                      </button>
                    </div>

                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      {viewModel.consultationSummary.sections.map((section) => (
                        <div
                          key={section.id}
                          className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                        >
                          <div className="text-sm font-semibold text-white">{section.title}</div>
                          <p className="mt-2 text-sm leading-7 text-slate-300/88">{section.content}</p>
                        </div>
                      ))}
                    </div>
                  </GlassCard>
                ) : consultationSession ? (
                  <GlassCard className="p-5">
                    <div className="flex items-center gap-2 text-primary-200">
                      <ClipboardList className="h-5 w-5" />
                      <h2 className="text-lg font-semibold text-white">咨询摘要</h2>
                    </div>
                    <p className="mt-3 text-sm leading-7 text-slate-200/88">
                      {consultationSession.chief_complaint_summary || "暂无可展示的咨询摘要。"}
                    </p>
                  </GlassCard>
                ) : null}

                {symptomInsights.length || highRiskInsights.length ? (
                  <GlassCard className="p-5">
                    <div className="flex items-center gap-2 text-primary-200">
                      <Layers3 className="h-5 w-5" />
                      <h2 className="text-lg font-semibold text-white">结构化线索</h2>
                    </div>

                    {symptomInsights.length ? (
                      <div className="mt-4">
                        <div className="text-sm font-semibold text-white">症状筛查结构化结果</div>
                        <div className="mt-3 grid gap-3 md:grid-cols-2">
                          {symptomInsights.map((item) => (
                            <div
                              key={`symptom-${item.label}`}
                              className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                            >
                              <div className="text-xs uppercase tracking-[0.16em] text-slate-400">
                                {item.label}
                              </div>
                              <div className="mt-2 text-sm leading-6 text-white/90">{item.value}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {highRiskInsights.length ? (
                      <div className={cn("mt-4", symptomInsights.length ? "border-t border-white/10 pt-4" : "")}>
                        <div className="text-sm font-semibold text-white">高风险筛查结果</div>
                        <div className="mt-3 grid gap-3 md:grid-cols-2">
                          {highRiskInsights.map((item) => (
                            <div
                              key={`risk-${item.label}`}
                              className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                            >
                              <div className="text-xs uppercase tracking-[0.16em] text-slate-400">
                                {item.label}
                              </div>
                              <div className="mt-2 text-sm leading-6 text-white/90">{item.value}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </GlassCard>
                ) : null}

                {transcriptPreview.length ? (
                  <GlassCard className="p-5">
                    <div className="flex items-center gap-2 text-primary-200">
                      <MessageSquareText className="h-5 w-5" />
                      <h2 className="text-lg font-semibold text-white">对话回看</h2>
                    </div>
                    <div className="mt-4 space-y-3">
                      {transcriptPreview.map((entry) => (
                        <div
                          key={`${entry.sequence}-${entry.created_at || entry.updated_at || entry.text}`}
                          className={cn(
                            "rounded-2xl border px-4 py-3",
                            entry.speaker === "doctor"
                              ? "border-primary-300/18 bg-primary-500/10"
                              : "border-white/10 bg-white/[0.04]",
                          )}
                        >
                          <div className="text-xs font-medium tracking-[0.16em] text-slate-400">
                            {entry.speaker === "doctor" ? "数字医生" : "受试者"}
                          </div>
                          <div className="mt-2 text-sm leading-7 text-white/90">{entry.text}</div>
                        </div>
                      ))}
                    </div>
                  </GlassCard>
                ) : null}
              </div>

              <div className="space-y-4">
                <GlassCard className="p-5">
                  <div className="flex items-center gap-2 text-primary-200">
                    <CalendarClock className="h-5 w-5" />
                    <h2 className="text-lg font-semibold text-white">就诊时间线</h2>
                  </div>
                  <div className="mt-4">
                    <EncounterTimeline events={encounter.timeline} />
                  </div>
                </GlassCard>

                <GlassCard className="p-5">
                  <div className="flex items-center gap-2 text-primary-200">
                    <Layers3 className="h-5 w-5" />
                    <h2 className="text-lg font-semibold text-white">关键元数据</h2>
                  </div>
                  <div className="mt-4 space-y-4 text-sm">
                    <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                      <div className="text-xs uppercase tracking-[0.16em] text-slate-400">Encounter ID</div>
                      <div className="mt-2 break-all text-white/90">{encounter.id}</div>
                    </div>

                    {encounter.consultation?.id ? (
                      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                        <div className="text-xs uppercase tracking-[0.16em] text-slate-400">Consultation Session</div>
                        <div className="mt-2 break-all text-white/90">{encounter.consultation.id}</div>
                      </div>
                    ) : null}

                    {encounter.assessment?.id ? (
                      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                        <div className="text-xs uppercase tracking-[0.16em] text-slate-400">Assessment Session</div>
                        <div className="mt-2 break-all text-white/90">{encounter.assessment.id}</div>
                      </div>
                    ) : null}

                    {encounter.consultation?.chief_complaint_raw_text ? (
                      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                        <div className="text-xs uppercase tracking-[0.16em] text-slate-400">主诉原文</div>
                        <div className="mt-2 text-sm leading-7 text-white/90">
                          {encounter.consultation.chief_complaint_raw_text}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </GlassCard>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {activeDrawer ? (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            aria-label="关闭详情抽屉遮罩"
            onClick={() => setActiveDrawer(null)}
            className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
          />

          <div className="absolute inset-4 mx-auto h-[calc(100vh-2rem)] max-w-6xl md:inset-8 md:h-[calc(100vh-4rem)]">
            {activeDrawer.kind === "consultation" ? (
              <ConsultationSummaryDrawer
                open
                summary={viewModel.consultationSummary}
                onClose={() => setActiveDrawer(null)}
              />
            ) : (
              <DetailDrawer
                open
                detail={selectedScaleDetail}
                onClose={() => setActiveDrawer(null)}
              />
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
