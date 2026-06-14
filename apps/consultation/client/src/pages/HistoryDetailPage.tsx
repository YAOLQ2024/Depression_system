import { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import {
  CalendarClock,
  ClipboardList,
  Download,
  Hash,
  Layers3,
  Loader2,
  MessageSquareText,
} from "lucide-react";
import { useParams } from "react-router-dom";
import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { EncounterTimeline } from "../components/EncounterTimeline";
import { Header } from "../components/Header";
import {
  buildResultPageViewModel,
  ConsultationSummaryDrawer,
  DetailDrawer,
  SummaryDashboard,
} from "../features/result-page";
import {
  buildEncounterAssessmentSession,
  buildEncounterConsultationSession,
  buildHistoryInsightItems,
  buildFullTranscriptGroups,
  getEncounterRiskFrontDisplay,
  getEncounterRiskSummary,
} from "../features/history/adapter";
import { useHistoryDetail } from "../hooks/useHistoryDetail";
import { cn } from "../lib/utils";
import { getAssessmentScaleDetail } from "../services/api/assessment.api";
import { downloadEncounterPdf } from "../services/api/consultation.api";
import type { AssessmentScaleDetail } from "../types";

const STATUS_LABELS: Record<string, string> = { draft: "草稿", in_progress: "进行中", paused: "已暂停", completed: "已完成" };
const FLOW_LABELS: Record<string, string> = { consultation: "问诊阶段", assessment: "量表评估阶段" };

type ActiveDrawerState = { kind: "scale"; scaleId: string } | { kind: "consultation" } | null;

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (v: number) => String(v).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const n = value.trim();
  return n ? n : null;
}

function riskBadgeClasses(label: string | null) {
  if (!label) return "bg-slate-50 text-slate-500 ring-slate-200";
  if (label.includes("高") || label.includes("重") || label.includes("危")) return "bg-rose-50 text-rose-600 ring-rose-200";
  if (label.includes("中") || label.includes("关注")) return "bg-amber-50 text-amber-600 ring-amber-200";
  if (label.includes("低") || label.includes("轻") || label.includes("正常")) return "bg-emerald-50 text-emerald-600 ring-emerald-200";
  return "bg-violet-50 text-violet-600 ring-violet-200";
}

/* ─── 浅色卡片 ─── */
function LightCard({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("rounded-2xl bg-white/80 shadow-sm ring-1 ring-black/[0.04] backdrop-blur-sm", className)}>{children}</div>;
}

/* ─── Section ─── */
function Section({ icon: Icon, title, children, delay = 0, action }: { icon: React.ElementType; title: string; children: React.ReactNode; delay?: number; action?: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay }}>
      <LightCard className="p-5 md:p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-100 text-violet-500"><Icon className="h-4 w-4" /></div>
            <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          </div>
          {action}
        </div>
        {children}
      </LightCard>
    </motion.div>
  );
}

/* ─── Skeleton ─── */
function DetailSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="rounded-2xl bg-white/80 p-6 ring-1 ring-black/[0.04]">
        <div className="mb-4 flex gap-2"><div className="h-6 w-16 rounded-full bg-violet-100" /><div className="h-6 w-20 rounded-full bg-violet-50" /></div>
        <div className="h-4 w-full rounded-full bg-slate-100" /><div className="mt-2 h-4 w-2/3 rounded-full bg-slate-100" />
        <div className="mt-6 grid gap-3 md:grid-cols-3">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-28 rounded-xl bg-slate-50 ring-1 ring-black/[0.03]" />)}</div>
      </div>
    </div>
  );
}

/* ─── 背景装饰 ─── */
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

export default function HistoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { state: appState } = useConsultationAppContext();
  const { state, reload } = useHistoryDetail(id);

  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [activeDrawer, setActiveDrawer] = useState<ActiveDrawerState>(null);
  const [assessmentScaleDetails, setAssessmentScaleDetails] = useState<Record<string, AssessmentScaleDetail>>({});
  const [scaleDetailLoadErrors, setScaleDetailLoadErrors] = useState<Record<string, string>>({});

  const encounter = state.encounter;
  const consultationSession = useMemo(() => buildEncounterConsultationSession(encounter), [encounter]);
  const assessmentSession = useMemo(() => buildEncounterAssessmentSession(encounter), [encounter]);
  const riskSummary = useMemo(() => getEncounterRiskSummary(encounter), [encounter]);
  const riskFrontDisplay = useMemo(() => getEncounterRiskFrontDisplay(encounter), [encounter]);

  const completedScaleIds = useMemo(() => {
    const slugs = (assessmentSession?.results || []).map((r) => r.scale_slug);
    return slugs.filter((slug, i) => Boolean(slug) && slugs.indexOf(slug) === i);
  }, [assessmentSession]);

  useEffect(() => {
    const sessionId = assessmentSession?.session_id || null;
    if (!sessionId || !completedScaleIds.length) { setAssessmentScaleDetails({}); setScaleDetailLoadErrors({}); return; }
    let cancelled = false;
    void (async () => {
      const settled = await Promise.allSettled(completedScaleIds.map(async (slug) => ({ scaleSlug: slug, detail: await getAssessmentScaleDetail(sessionId, slug) })));
      if (cancelled) return;
      const nextD: Record<string, AssessmentScaleDetail> = {};
      const nextE: Record<string, string> = {};
      settled.forEach((r, i) => {
        const slug = completedScaleIds[i];
        if (r.status === "fulfilled") { nextD[slug] = r.value.detail; return; }
        nextE[slug] = r.reason instanceof Error ? r.reason.message : "详细作答加载失败，请稍后重试。";
      });
      setAssessmentScaleDetails(nextD);
      setScaleDetailLoadErrors(nextE);
    })();
    return () => { cancelled = true; };
  }, [assessmentSession?.session_id, completedScaleIds]);

  const viewModel = useMemo(
    () => buildResultPageViewModel({ assessment: assessmentSession, assessmentCatalog: appState.assessmentCatalog, assessmentScaleDetails, consultation: consultationSession }),
    [appState.assessmentCatalog, assessmentScaleDetails, assessmentSession, consultationSession],
  );

  const selectedScaleId = activeDrawer?.kind === "scale" ? activeDrawer.scaleId : null;
  const selectedScaleDetail = useMemo(() => {
    if (!selectedScaleId) return null;
    const detail = viewModel.scaleDetails[selectedScaleId] || null;
    if (!detail) return null;
    const err = scaleDetailLoadErrors[selectedScaleId];
    return err ? { ...detail, itemResultsReady: false, itemResultsNotice: err } : detail;
  }, [scaleDetailLoadErrors, selectedScaleId, viewModel.scaleDetails]);

  const modules = useMemo(
    () => viewModel.modules.map((m) =>
      m.id === "consultation-summary" && viewModel.consultationSummary
        ? { ...m, actionLabel: "查看详情", onAction: () => setActiveDrawer({ kind: "consultation" }) }
        : m,
    ),
    [viewModel.consultationSummary, viewModel.modules],
  );

  const symptomInsights = useMemo(() => buildHistoryInsightItems(consultationSession?.current_history_structured_result), [consultationSession]);
  const highRiskInsights = useMemo(() => buildHistoryInsightItems(consultationSession?.high_risk_screening_result), [consultationSession]);
  const transcriptGroups = useMemo(() => buildFullTranscriptGroups(consultationSession?.subtitle_history, assessmentScaleDetails), [consultationSession, assessmentScaleDetails]);

  const summaryMessage =
    asString(riskFrontDisplay?.message) || consultationSession?.digital_human_consultation_summary ||
    consultationSession?.chief_complaint_stage_summary || encounter?.consultation?.chief_complaint_summary ||
    "本次历史记录已汇总，可查看问诊摘要、量表结果与时间线。";
  const riskLevelLabel = asString(riskSummary?.risk_level_label) || asString(riskFrontDisplay?.risk_level_label) || encounter?.assessment_results[0]?.interpretation_label || null;
  const requiredScaleLabels = viewModel.consultationSummary?.requiredScaleLabels || [];

  const handleDownloadPdf = async () => {
    if (!id) return;
    setDownloading(true); setDownloadError(null);
    try { await downloadEncounterPdf(id); }
    catch (err: any) { setDownloadError(err?.message || "下载失败"); }
    finally { setDownloading(false); }
  };

  const isCompleted = encounter?.status === "completed";

  return (
    <div className="min-h-screen bg-[#f8f7ff]">
      <BackgroundDecor />
      <div className="relative z-20"><Header title="历史就诊详情" /></div>

      <div className="relative z-10 w-full px-6 pt-6 pb-10 md:px-10 lg:px-14">
        {state.error && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-20 text-center">
            <p className="text-sm text-rose-500">{state.error}</p>
            <button onClick={reload} className="mt-3 rounded-xl border border-slate-200 bg-white px-5 py-2 text-sm text-slate-600 shadow-sm hover:bg-slate-50 cursor-pointer">重试</button>
          </motion.div>
        )}
        {downloadError && <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">{downloadError}</motion.div>}
        {state.loading && !encounter && <DetailSkeleton />}

        {encounter ? (
          <div className="space-y-4">
            {/* ─── 评估结果（顶部主卡） ─── */}
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
              <LightCard className="overflow-hidden">
                {/* 渐变线 */}
                <div className="h-1 bg-gradient-to-r from-violet-400 via-blue-400 to-violet-400" />

                {/* 信息头：标签 + 摘要 + 指标 + PDF */}
                <div className="border-b border-slate-100 px-5 py-4 md:px-6">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0 flex-1">
                      {/* 标签行 */}
                      <div className="mb-2.5 flex flex-wrap items-center gap-2">
                        <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1", isCompleted ? "bg-violet-50 text-violet-600 ring-violet-200" : "bg-amber-50 text-amber-600 ring-amber-200")}>
                          {isCompleted ? <span className="h-1.5 w-1.5 rounded-full bg-violet-500" /> : <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />}
                          {STATUS_LABELS[encounter.status] || encounter.status}
                        </span>
                        <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-[11px] font-medium text-blue-600 ring-1 ring-blue-200">
                          {FLOW_LABELS[encounter.current_flow_type] || encounter.current_flow_type}
                        </span>
                        {riskLevelLabel && <span className={cn("rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1", riskBadgeClasses(riskLevelLabel))}>{riskLevelLabel}</span>}
                        {requiredScaleLabels.map((label) => <span key={label} className="rounded-full bg-violet-50/80 px-2.5 py-0.5 text-[11px] font-medium text-violet-500 ring-1 ring-violet-100">{label}</span>)}
                      </div>
                      {/* 摘要 */}
                      <p className="text-sm leading-relaxed text-slate-600 line-clamp-2">{summaryMessage}</p>
                      {/* 指标行 */}
                      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-slate-500">
                        <span>创建：<span className="font-medium text-slate-700">{formatDateTime(encounter.created_at)}</span></span>
                        <span>完成：<span className="font-medium text-slate-700">{formatDateTime(encounter.completed_at)}</span></span>
                        <span>医生：<span className="font-medium text-slate-700">{consultationSession?.assigned_doctor_persona || "—"}</span></span>
                        <span>量表：<span className="font-medium text-slate-700">{viewModel.scales.length || encounter.assessment_results.length || 0} 项</span></span>
                      </div>
                    </div>

                    {/* PDF 下载 */}
                    {isCompleted && (
                      <button onClick={handleDownloadPdf} disabled={downloading} className="shrink-0 inline-flex items-center gap-2 rounded-xl border border-violet-200 bg-white/80 px-4 py-2.5 text-sm font-medium text-violet-600 shadow-sm transition-all hover:bg-violet-50 disabled:cursor-wait disabled:opacity-50 cursor-pointer">
                        {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                        {downloading ? "生成中..." : "下载 PDF"}
                      </button>
                    )}
                  </div>
                </div>

                {/* 评估仪表盘 */}
                <div className="p-4 md:p-5">
                  {viewModel.hasAssessment ? (
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
                      theme="light"
                    />
                  ) : (
                    <div className="flex items-start gap-3 py-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100"><Layers3 className="h-5 w-5 text-slate-400" /></div>
                      <div>
                        <h2 className="text-base font-semibold text-slate-900">量表结果</h2>
                        <p className="mt-1.5 text-sm leading-7 text-slate-500">本次记录尚未形成完整的量表评估结果，当前详情页仍保留问诊摘要、结构化线索和时间线，方便继续回看。</p>
                      </div>
                    </div>
                  )}
                </div>
              </LightCard>
            </motion.div>

            {/* ─── 双栏布局 ─── */}
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_360px]">
              <div className="space-y-4">
                {viewModel.consultationSummary ? (
                  <Section icon={ClipboardList} title="咨询摘要" delay={0.15}
                    action={<button onClick={() => setActiveDrawer({ kind: "consultation" })} className="rounded-lg bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-600 ring-1 ring-violet-200 transition-all hover:bg-violet-100 cursor-pointer">查看完整摘要</button>}
                  >
                    <p className="text-sm leading-7 text-slate-600">{viewModel.consultationSummary.overallSummary}</p>
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      {viewModel.consultationSummary.sections.map((s) => (
                        <div key={s.id} className="rounded-xl bg-slate-50/80 p-4 ring-1 ring-black/[0.03] transition-colors hover:bg-slate-50">
                          <div className="text-sm font-medium text-slate-800">{s.title}</div>
                          <p className="mt-1.5 text-sm leading-6 text-slate-500">{s.content}</p>
                        </div>
                      ))}
                    </div>
                  </Section>
                ) : consultationSession ? (
                  <Section icon={ClipboardList} title="咨询摘要" delay={0.15}>
                    <p className="text-sm leading-7 text-slate-600">{consultationSession.chief_complaint_summary || "暂无可展示的咨询摘要。"}</p>
                  </Section>
                ) : null}

                {symptomInsights.length > 0 || highRiskInsights.length > 0 ? (
                  <Section icon={Layers3} title="结构化线索" delay={0.2}>
                    {symptomInsights.length > 0 && (
                      <div>
                        <div className="mb-3 text-sm font-medium text-slate-700">症状筛查结构化结果</div>
                        <div className="grid gap-3 md:grid-cols-2">
                          {symptomInsights.map((item) => (
                            <div key={`symptom-${item.label}`} className="rounded-xl bg-slate-50/80 p-4 ring-1 ring-black/[0.03]">
                              <div className="text-xs font-medium uppercase tracking-widest text-slate-400">{item.label}</div>
                              <div className="mt-2 text-sm leading-6 text-slate-700">{item.value}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {highRiskInsights.length > 0 && (
                      <div className={cn(symptomInsights.length > 0 ? "mt-5 border-t border-slate-100 pt-5" : "")}>
                        <div className="mb-3 text-sm font-medium text-rose-600">高风险筛查结果</div>
                        <div className="grid gap-3 md:grid-cols-2">
                          {highRiskInsights.map((item) => (
                            <div key={`risk-${item.label}`} className="rounded-xl bg-rose-50/60 p-4 ring-1 ring-rose-100">
                              <div className="text-xs font-medium uppercase tracking-widest text-rose-400">{item.label}</div>
                              <div className="mt-2 text-sm leading-6 text-slate-700">{item.value}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </Section>
                ) : null}
              </div>

              <div className="space-y-4">
                <Section icon={CalendarClock} title="就诊时间线" delay={0.2}>
                  <EncounterTimeline events={encounter.timeline} />
                </Section>

                <Section icon={Hash} title="关键元数据" delay={0.25}>
                  <div className="space-y-3">
                    {[
                      { label: "就诊记录 ID", value: encounter.id },
                      encounter.consultation?.id ? { label: "问诊会话 ID", value: encounter.consultation.id } : null,
                      encounter.assessment?.id ? { label: "量表评估 ID", value: encounter.assessment.id } : null,
                    ].filter(Boolean).map((item) => (
                      <div key={item!.label} className="rounded-xl bg-slate-50/80 p-4 ring-1 ring-black/[0.03]">
                        <div className="text-xs font-medium text-slate-400">{item!.label}</div>
                        <div className="mt-2 break-all font-mono text-xs text-slate-600">{item!.value}</div>
                      </div>
                    ))}
                    {encounter.consultation?.chief_complaint_raw_text && (
                      <div className="rounded-xl bg-slate-50/80 p-4 ring-1 ring-black/[0.03]">
                        <div className="text-xs font-medium uppercase tracking-widest text-slate-400">主诉原文</div>
                        <div className="mt-2 text-sm leading-7 text-slate-600">{encounter.consultation.chief_complaint_raw_text}</div>
                      </div>
                    )}
                  </div>
                </Section>
              </div>
            </div>

            {/* ─── 对话回看（全宽，按阶段分组） ─── */}
            {transcriptGroups.length > 0 && (
              <Section icon={MessageSquareText} title="对话回看" delay={0.25}>
                <div className="space-y-8">
                  {transcriptGroups.map((group, gIdx) => {
                    const prevGroup = gIdx > 0 ? transcriptGroups[gIdx - 1] : null;
                    const showSectionDivider = gIdx === 0 || (prevGroup && prevGroup.section !== group.section);
                    const qaCount = group.entries.filter((e) => e.speaker === "doctor").length;

                    return (
                      <div key={group.stageId}>
                        {/* 咨询 ↔ 量表 分区线 */}
                        {showSectionDivider && (
                          <div className={cn("flex items-center gap-3", gIdx > 0 ? "mb-8 mt-2" : "mb-4")}>
                            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-300 to-transparent" />
                            <span className="text-xs font-semibold text-slate-400">
                              {group.section === "assessment" ? "量表评估阶段" : "咨询问诊阶段"}
                            </span>
                            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-300 to-transparent" />
                          </div>
                        )}

                        {/* 阶段标题 */}
                        <div className="mb-3 flex items-center gap-2">
                          <div className="h-5 w-1 rounded-full bg-gradient-to-b from-violet-400 to-blue-400" />
                          <span className="text-sm font-semibold text-slate-700">{group.stageLabel}</span>
                          <span className="text-xs text-slate-400">{qaCount} 条对话</span>
                        </div>

                        {/* 对话条目 */}
                        <div className="space-y-2">
                          {group.entries.map((entry, idx) => {
                            const isDoctor = entry.speaker === "doctor";
                            const hasNewline = entry.text.includes("\n");
                            return (
                              <motion.div
                                key={`${group.stageId}-${idx}`}
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.3, delay: gIdx * 0.03 + idx * 0.02 }}
                                className={cn(
                                  "rounded-xl px-5 py-3.5 ring-1",
                                  isDoctor ? "bg-violet-50/80 ring-violet-200/60" : "bg-emerald-50/60 ring-emerald-200/50",
                                )}
                              >
                                <span className={cn("text-xs font-bold", isDoctor ? "text-violet-600" : "text-emerald-600")}>
                                  {isDoctor ? "数字医生" : "受试者"}
                                </span>
                                <div className={cn("mt-1.5 text-[15px] text-slate-800", hasNewline ? "space-y-3 leading-7 whitespace-pre-line" : "leading-8")}>
                                  {entry.text}
                                </div>
                              </motion.div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Section>
            )}
          </div>
        ) : null}
      </div>

      {activeDrawer && (
        <div className="fixed inset-0 z-50">
          <motion.button initial={{ opacity: 0 }} animate={{ opacity: 1 }} type="button" aria-label="关闭详情抽屉遮罩" onClick={() => setActiveDrawer(null)} className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm" />
          <motion.div initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} transition={{ type: "spring", damping: 28, stiffness: 300 }} className="absolute inset-4 mx-auto h-[calc(100vh-2rem)] max-w-6xl md:inset-8 md:h-[calc(100vh-4rem)]">
            {activeDrawer.kind === "consultation" ? (
              <ConsultationSummaryDrawer open summary={viewModel.consultationSummary} onClose={() => setActiveDrawer(null)} />
            ) : (
              <DetailDrawer open detail={selectedScaleDetail} onClose={() => setActiveDrawer(null)} />
            )}
          </motion.div>
        </div>
      )}
    </div>
  );
}
