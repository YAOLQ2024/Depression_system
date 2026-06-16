import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  CalendarClock,
  ClipboardList,
  Flag,
  Leaf,
  Loader2,
  Stethoscope,
} from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { Header } from "../components/Header";
import {
  AdviceCard,
  buildResultPageViewModel,
  GlassCard,
  ResultThemeContext,
  RingChart,
  ScaleItemResultTable,
  SeverityBadge,
  TrendLineChart,
} from "../features/result-page";
import {
  buildEncounterAssessmentSession,
  buildEncounterConsultationSession,
} from "../features/history/adapter";
import { useHistoryDetail } from "../hooks/useHistoryDetail";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";
import { getAssessmentScaleDetail } from "../services/api/assessment.api";
import type { AssessmentScaleDetail } from "../types";

function BackgroundDecor() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-[400px] bg-gradient-to-b from-violet-100/60 via-blue-50/40 to-transparent" />
      <div className="absolute -left-32 top-[120px] h-[500px] w-[500px] rounded-full bg-violet-200/30 blur-[100px]" />
      <div className="absolute -right-32 top-[60px] h-[400px] w-[400px] rounded-full bg-blue-200/25 blur-[100px]" />
      <svg className="absolute inset-0 h-full w-full opacity-30" xmlns="http://www.w3.org/2000/svg">
        <circle cx="10%" cy="25%" r="3" fill="#8b5cf6" opacity="0.4" />
        <circle cx="85%" cy="18%" r="4" fill="#6366f1" opacity="0.3" />
        <circle cx="75%" cy="55%" r="2.5" fill="#3b82f6" opacity="0.35" />
      </svg>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="rounded-2xl bg-white/80 p-6 ring-1 ring-black/[0.04]">
        <div className="mb-4 h-10 w-40 rounded-xl bg-violet-100" />
        <div className="h-8 w-60 rounded-xl bg-slate-100" />
        <div className="mt-3 h-4 w-80 rounded-xl bg-slate-100" />
        <div className="mt-6 grid gap-3 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="h-32 rounded-2xl bg-slate-50 ring-1 ring-black/[0.03]" />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function HistoryScaleDetailPage() {
  const navigate = useNavigate();
  const { id, scaleId } = useParams<{ id: string; scaleId: string }>();
  const { state: appState } = useConsultationAppContext();
  const { state, reload } = useHistoryDetail(id);
  const [scaleDetail, setScaleDetail] = useState<AssessmentScaleDetail | null>(null);
  const [scaleDetailLoading, setScaleDetailLoading] = useState(false);
  const [scaleDetailError, setScaleDetailError] = useState<string | null>(null);

  const encounter = state.encounter;
  const consultationSession = useMemo(() => buildEncounterConsultationSession(encounter), [encounter]);
  const assessmentSession = useMemo(() => buildEncounterAssessmentSession(encounter), [encounter]);
  const historyDetailPath = id ? `${APP_PATHS.history}/${id}` : APP_PATHS.history;

  useEffect(() => {
    const sessionId = assessmentSession?.session_id;
    if (!sessionId || !scaleId) {
      setScaleDetail(null);
      setScaleDetailError(null);
      setScaleDetailLoading(false);
      return;
    }

    let cancelled = false;
    setScaleDetail(null);
    setScaleDetailError(null);
    setScaleDetailLoading(true);

    void (async () => {
      try {
        const detail = await getAssessmentScaleDetail(sessionId, scaleId);
        if (cancelled) {
          return;
        }
        setScaleDetail(detail);
      } catch (error: any) {
        if (cancelled) {
          return;
        }
        setScaleDetailError(error?.message || "量表详细结果加载失败，请稍后重试。");
      } finally {
        if (!cancelled) {
          setScaleDetailLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [assessmentSession?.session_id, scaleId]);

  const viewModel = useMemo(
    () =>
      buildResultPageViewModel({
        assessment: assessmentSession,
        assessmentCatalog: appState.assessmentCatalog,
        assessmentScaleDetails:
          scaleDetail && scaleId
            ? { [scaleId]: scaleDetail }
            : {},
        consultation: consultationSession,
      }),
    [appState.assessmentCatalog, assessmentSession, consultationSession, scaleDetail, scaleId],
  );

  const detail = scaleId ? viewModel.scaleDetails[scaleId] || null : null;
  const hasAssessment = Boolean(assessmentSession);
  const hasScale = Boolean(detail);
  const itemResultsReady = Boolean(scaleDetail);

  return (
    <div className="min-h-screen bg-[#f8f7ff]">
      <BackgroundDecor />
      <div className="relative z-20">
        <Header title="量表详细报告" />
      </div>

      <div className="relative z-10 w-full px-6 pt-6 pb-10 md:px-10 lg:px-14">
        {state.error ? (
          <div className="py-20 text-center">
            <p className="text-sm text-rose-500">{state.error}</p>
            <button
              onClick={reload}
              className="mt-3 rounded-xl border border-slate-200 bg-white px-5 py-2 text-sm text-slate-600 shadow-sm transition-colors hover:bg-slate-50"
            >
              重试
            </button>
          </div>
        ) : null}

        {state.loading && !encounter ? <DetailSkeleton /> : null}

        {encounter && !hasAssessment ? (
          <div className="rounded-2xl bg-white/85 p-8 text-center shadow-sm ring-1 ring-black/[0.04]">
            <p className="text-sm text-slate-500">这条历史记录还没有量表评估结果。</p>
            <button
              onClick={() => navigate(historyDetailPath)}
              className="mt-4 inline-flex items-center gap-2 rounded-xl border border-violet-200 bg-violet-50 px-4 py-2 text-sm font-medium text-violet-600 transition-colors hover:bg-violet-100"
            >
              <ArrowLeft className="h-4 w-4" />
              返回历史详情
            </button>
          </div>
        ) : null}

        {encounter && hasAssessment ? (
          <ResultThemeContext.Provider value="light">
            <div className="space-y-4">
              <GlassCard className="overflow-hidden">
                <div className="h-1 bg-gradient-to-r from-violet-400 via-blue-400 to-violet-400" />
                <div className="border-b border-slate-100 px-5 py-4 md:px-6">
                  <button
                    onClick={() => navigate(historyDetailPath)}
                    className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    返回历史详情
                  </button>

                  <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="mb-3 flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-violet-50 px-2.5 py-0.5 text-[11px] font-semibold text-violet-600 ring-1 ring-violet-200">
                          {detail?.name || scaleId}
                        </span>
                        {detail?.fullName ? (
                          <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-[11px] font-medium text-blue-600 ring-1 ring-blue-200">
                            {detail.fullName}
                          </span>
                        ) : null}
                        {detail?.completedAt ? (
                          <span className="rounded-full bg-slate-50 px-2.5 py-0.5 text-[11px] font-medium text-slate-500 ring-1 ring-slate-200">
                            评估时间 {detail.completedAt}
                          </span>
                        ) : null}
                      </div>
                      <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                        {detail?.title || "量表详细报告"}
                      </h1>
                      <p className="mt-2 text-sm leading-7 text-slate-500">
                        查看本次量表的得分、严重程度、逐题作答与结果解读，页面样式与历史就诊详情保持一致。
                      </p>
                    </div>

                    <div className="shrink-0">
                      {scaleDetailLoading ? (
                        <div className="inline-flex items-center gap-2 rounded-xl bg-violet-50 px-3.5 py-2 text-sm font-medium text-violet-600 ring-1 ring-violet-200">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          正在加载逐题明细
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>

                {hasScale ? (
                  <div className="p-4 md:p-5">
                    <GlassCard className="p-4">
                      <div className="grid gap-4 md:grid-cols-[minmax(220px,0.95fr)_1px_minmax(0,0.85fr)_1px_minmax(0,0.85fr)] md:items-center">
                        <div className="flex justify-center">
                          <RingChart
                            score={detail?.score ?? 0}
                            maxScore={detail?.maxScore ?? 100}
                            label="本次得分"
                            size={150}
                            strokeWidth={14}
                            valueLabel={detail?.score === null ? "--" : undefined}
                          />
                        </div>
                        <div className="hidden h-24 w-px bg-gradient-to-b from-transparent via-slate-200 to-transparent md:block" />
                        <div className="flex flex-col items-center text-center md:items-start md:text-left">
                          <div className="mb-4 text-sm font-semibold tracking-[0.06em] text-slate-600">疾病严重程度</div>
                          <SeverityBadge level={detail?.severity || "待接入"} className="px-5 py-3 text-xl font-semibold tracking-wide md:text-2xl" />
                        </div>
                        <div className="hidden h-24 w-px bg-gradient-to-b from-transparent via-slate-200 to-transparent md:block" />
                        <div className="flex flex-col items-center text-center md:items-start md:text-left">
                          <div className="mb-4 text-sm font-semibold tracking-[0.06em] text-slate-600">风险提示</div>
                          <SeverityBadge level={detail?.riskLabel || "待补充"} className="px-5 py-3 text-xl font-semibold tracking-wide md:text-2xl" />
                        </div>
                      </div>
                    </GlassCard>

                    <div className="mt-4 grid gap-3 md:grid-cols-3">
                      <GlassCard className="p-4">
                        <div className="mb-1 text-sm font-semibold tracking-[0.06em] text-slate-500">标准化得分</div>
                        <div className="text-xl font-semibold text-slate-900">
                          {detail?.normalizedScore !== null && detail?.normalizedScore !== undefined
                            ? `${detail.normalizedScore}`
                            : "--"}
                        </div>
                      </GlassCard>
                      <GlassCard className="p-4">
                        <div className="mb-1 text-sm font-semibold tracking-[0.06em] text-slate-500">题目完成数</div>
                        <div className="text-xl font-semibold text-slate-900">
                          {detail?.answeredItemCount !== null && detail?.answeredItemCount !== undefined
                            ? `${detail.answeredItemCount}/${detail.configuredItemCount || "--"}`
                            : detail?.configuredItemCount
                              ? `--/${detail.configuredItemCount}`
                              : "--"}
                        </div>
                      </GlassCard>
                      <GlassCard className="p-4">
                        <div className="mb-1 text-sm font-semibold tracking-[0.06em] text-slate-500">计分说明</div>
                        <div className="text-xl font-semibold text-slate-900">{detail?.scoreMethodLabel || "待补充"}</div>
                      </GlassCard>
                    </div>
                  </div>
                ) : (
                  <div className="p-5 md:p-6">
                    <div className="rounded-2xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-700">
                      当前历史记录中未找到该量表的详细结果，请返回上一页重新选择。
                    </div>
                  </div>
                )}
              </GlassCard>

              {hasScale ? (
                <>
                  {detail?.riskFlags?.length ? (
                    <GlassCard className="p-5 md:p-6">
                      <div className="mb-4 flex items-center gap-2 text-slate-900">
                        <Flag className="h-5 w-5 text-rose-500" />
                        <h2 className="text-base font-semibold">风险标记</h2>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {detail.riskFlags.map((flag) => (
                          <span
                            key={`${flag.flag}-${flag.itemId || flag.label}`}
                            className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-sm font-medium text-rose-600"
                          >
                            {flag.label}
                          </span>
                        ))}
                      </div>
                    </GlassCard>
                  ) : null}

                  {detail?.verificationStatus && detail.verificationStatus !== "verified" ? (
                    <GlassCard className="border border-amber-200 bg-amber-50/90 p-4">
                      <p className="text-sm leading-6 text-amber-700">
                        当前量表的计分配置仍带有待复核标记，页面先按现有后端返回展示，后续以正式 contract 为准。
                      </p>
                    </GlassCard>
                  ) : null}

                  <div className="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)]">
                    <GlassCard className="p-5 md:p-6">
                      <div className="mb-4 flex items-center gap-2 text-slate-900">
                        <ClipboardList className="h-5 w-5 text-violet-500" />
                        <h2 className="text-base font-semibold">结果说明</h2>
                      </div>
                      <div className="grid gap-3 md:grid-cols-2">
                        <AdviceCard
                          icon={<BookOpen className="h-5 w-5" />}
                          title="结果解读"
                          content={detail?.interpretation || "结果解读待接入。"}
                        />
                        <AdviceCard
                          icon={<AlertTriangle className="h-5 w-5" />}
                          title="风险提示"
                          content={detail?.riskHint || "风险提示待接入。"}
                          tone="amber"
                        />
                        <AdviceCard
                          icon={<Stethoscope className="h-5 w-5" />}
                          title="就诊建议"
                          content={detail?.clinicalAdvice || "就诊建议待接入。"}
                        />
                        <AdviceCard
                          icon={<Leaf className="h-5 w-5" />}
                          title="生活建议"
                          content={detail?.lifestyleAdvice || "生活建议待接入。"}
                          tone="emerald"
                        />
                      </div>
                    </GlassCard>

                    <GlassCard className="p-5 md:p-6">
                      <div className="mb-4 flex items-center gap-2 text-slate-900">
                        <CalendarClock className="h-5 w-5 text-violet-500" />
                        <h2 className="text-base font-semibold">历次趋势</h2>
                      </div>
                      <TrendLineChart
                        data={detail?.history || []}
                        className="p-0 shadow-none ring-0"
                        emptyLabel="当前还没有历次趋势数据，后续接入后会在这里展示。"
                      />
                    </GlassCard>
                  </div>

                  <GlassCard className="p-5 md:p-6">
                    <div className="mb-4 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 text-slate-900">
                        <ClipboardList className="h-5 w-5 text-violet-500" />
                        <h2 className="text-base font-semibold">逐题作答明细</h2>
                      </div>
                      {itemResultsReady ? (
                        <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-600 ring-1 ring-emerald-200">
                          已加载完整作答
                        </span>
                      ) : null}
                    </div>

                    {scaleDetailLoading ? (
                      <div className="flex min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/70">
                        <div className="inline-flex items-center gap-2 text-sm text-slate-500">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          正在加载逐题作答明细
                        </div>
                      </div>
                    ) : scaleDetailError ? (
                      <div className="rounded-2xl border border-rose-200 bg-rose-50/80 px-4 py-3 text-sm text-rose-600">
                        {scaleDetailError}
                      </div>
                    ) : itemResultsReady ? (
                      <ScaleItemResultTable items={detail?.items || []} notice={detail?.itemResultsNotice} />
                    ) : (
                      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-4 py-10 text-center text-sm text-slate-500">
                        暂无可展示的逐题作答明细。
                      </div>
                    )}
                  </GlassCard>
                </>
              ) : null}
            </div>
          </ResultThemeContext.Provider>
        ) : null}
      </div>
    </div>
  );
}
