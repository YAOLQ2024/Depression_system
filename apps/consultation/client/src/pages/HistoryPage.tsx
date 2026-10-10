import { motion } from "motion/react";
import {
  CalendarDays,
  FileText,
  Filter,
  Loader2,
  Plus,
  SearchX,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { APP_PATHS } from "../routes";
import { EncounterCard } from "../components/EncounterCard";
import { Header } from "../components/Header";
import { useHistoryList } from "../hooks/useHistoryList";
import { useResumeEncounter } from "../hooks/useResumeEncounter";
import type { EncounterSummary } from "../services/api/contracts";

/* ─── 筛选标签 ─── */
type FilterKey = "all" | "completed" | "in_progress";

const FILTER_TABS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "completed", label: "已完成" },
  { key: "in_progress", label: "进行中" },
];

/* ─── 统计卡片 ─── */
function StatCard({
  icon: Icon,
  label,
  value,
  color,
  delay,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      className="flex items-center gap-4 rounded-2xl bg-white/80 p-5 shadow-sm ring-1 ring-black/[0.04] backdrop-blur-sm transition-all hover:shadow-md hover:-translate-y-0.5"
    >
      <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${color} shadow-lg`}>
        <Icon className="h-6 w-6 text-white" />
      </div>
      <div>
        <div className="text-2xl font-bold text-slate-900">{value}</div>
        <div className="text-xs font-medium text-slate-500">{label}</div>
      </div>
    </motion.div>
  );
}

/* ─── 骨架屏 ─── */
function SkeletonRow() {
  return (
    <div className="animate-pulse flex items-center gap-6 rounded-2xl bg-white/80 p-5 ring-1 ring-black/[0.04]">
      <div className="h-10 w-10 rounded-xl bg-violet-100" />
      <div className="flex-1 space-y-2">
        <div className="h-4 w-48 rounded-full bg-slate-100" />
        <div className="h-3 w-72 rounded-full bg-slate-50" />
      </div>
      <div className="h-6 w-16 rounded-full bg-violet-50" />
      <div className="h-6 w-14 rounded-full bg-slate-100" />
      <div className="h-9 w-24 rounded-xl bg-violet-50" />
    </div>
  );
}

/* ─── 空状态 ─── */
function EmptyState({ hasFilter }: { hasFilter: boolean }) {
  const navigate = useNavigate();
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="flex flex-col items-center py-20 text-center"
    >
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-violet-50 to-blue-50 ring-1 ring-violet-100">
        <FileText className="h-10 w-10 text-violet-300" />
      </div>
      <h3 className="text-lg font-semibold text-slate-800">
        {hasFilter ? "没有匹配的记录" : "暂无就诊记录"}
      </h3>
      <p className="mt-2 max-w-sm text-sm text-slate-500">
        {hasFilter
          ? "尝试切换筛选条件查看更多记录"
          : "完成一次问诊后，您的就诊记录会出现在这里"}
      </p>
      {!hasFilter && (
        <button
          onClick={() => navigate(APP_PATHS.home)}
          className="mt-6 flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-blue-500 px-5 py-2.5 text-sm font-medium text-white shadow-md shadow-violet-500/20 transition-all hover:shadow-lg cursor-pointer"
        >
          <Plus className="h-4 w-4" />
          开始问诊
        </button>
      )}
    </motion.div>
  );
}

/* ─── 错误状态 ─── */
function ErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center py-16 text-center"
    >
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-rose-50 ring-1 ring-rose-100">
        <SearchX className="h-8 w-8 text-rose-400" />
      </div>
      <p className="text-sm text-rose-500">{error}</p>
      <button
        onClick={onRetry}
        className="mt-4 rounded-xl border border-slate-200 bg-white px-5 py-2 text-sm text-slate-600 shadow-sm transition-colors hover:bg-slate-50 cursor-pointer"
      >
        重试
      </button>
    </motion.div>
  );
}

/* ─── 背景装饰 ─── */
function BackgroundDecor() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      {/* 顶部渐变 */}
      <div className="absolute inset-x-0 top-0 h-[400px] bg-gradient-to-b from-violet-100/60 via-blue-50/40 to-transparent" />

      {/* 左侧大光斑 */}
      <div className="absolute -left-32 top-[120px] h-[500px] w-[500px] rounded-full bg-violet-200/30 blur-[100px]" />
      {/* 右侧大光斑 */}
      <div className="absolute -right-32 top-[60px] h-[400px] w-[400px] rounded-full bg-blue-200/25 blur-[100px]" />
      {/* 中部淡光 */}
      <div className="absolute left-1/2 top-[300px] h-[300px] w-[600px] -translate-x-1/2 rounded-full bg-indigo-100/20 blur-[80px]" />

      {/* 波浪装饰 SVG */}
      <svg
        className="absolute top-[460px] w-full opacity-40"
        viewBox="0 0 1440 120"
        fill="none"
        preserveAspectRatio="none"
        style={{ height: 120 }}
      >
        <path
          d="M0 60 C360 120 720 0 1080 60 C1260 90 1380 80 1440 60 V120 H0Z"
          fill="url(#wave1)"
        />
        <path
          d="M0 80 C300 40 600 100 900 70 C1100 50 1300 90 1440 80 V120 H0Z"
          fill="url(#wave2)"
        />
        <defs>
          <linearGradient id="wave1" x1="0" y1="0" x2="1440" y2="0">
            <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.06" />
            <stop offset="50%" stopColor="#6366f1" stopOpacity="0.04" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.06" />
          </linearGradient>
          <linearGradient id="wave2" x1="0" y1="0" x2="1440" y2="0">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.04" />
            <stop offset="50%" stopColor="#8b5cf6" stopOpacity="0.03" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.05" />
          </linearGradient>
        </defs>
      </svg>

      {/* 散落小圆点 */}
      <svg className="absolute inset-0 h-full w-full opacity-30" xmlns="http://www.w3.org/2000/svg">
        <circle cx="10%" cy="25%" r="3" fill="#8b5cf6" opacity="0.4" />
        <circle cx="85%" cy="18%" r="4" fill="#6366f1" opacity="0.3" />
        <circle cx="75%" cy="55%" r="2.5" fill="#3b82f6" opacity="0.35" />
        <circle cx="20%" cy="70%" r="3.5" fill="#8b5cf6" opacity="0.25" />
        <circle cx="50%" cy="40%" r="2" fill="#a78bfa" opacity="0.3" />
        <circle cx="90%" cy="75%" r="3" fill="#60a5fa" opacity="0.3" />
      </svg>
    </div>
  );
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const { state, loadInitial, loadMore } = useHistoryList();
  const {
    dialog,
    promptResume,
    cancelResume,
    confirmResume,
    isResuming,
    resumeError,
  } = useResumeEncounter();

  const [filter, setFilter] = useState<FilterKey>("all");

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  /* 统计数据 */
  const stats = useMemo(() => {
    const total = state.encounters.length;
    const completed = state.encounters.filter((e) => e.status === "completed").length;
    const inProgress = total - completed;
    const avgScore = (() => {
      const scored = state.encounters.filter((e) => e.phq9_score != null);
      if (!scored.length) return "—";
      const avg = scored.reduce((s, e) => s + (e.phq9_score ?? 0), 0) / scored.length;
      return avg.toFixed(1);
    })();
    return { total, completed, inProgress, avgScore };
  }, [state.encounters]);

  /* 筛选后列表 */
  const filtered = useMemo(() => {
    if (filter === "all") return state.encounters;
    if (filter === "completed") return state.encounters.filter((e) => e.status === "completed");
    return state.encounters.filter((e) => e.status !== "completed");
  }, [state.encounters, filter]);

  const handleContinue = (encounter: EncounterSummary) => promptResume(encounter);
  const handleViewDetail = (encounter: EncounterSummary) =>
    navigate(`${APP_PATHS.history}/${encounter.id}`);

  return (
    <div className="history-page min-h-screen bg-[#f8f7ff]">
      <BackgroundDecor />

      {/* 全局 Header */}
      <div className="relative z-20">
        <Header title="历史就诊记录" />
      </div>

      <div className="history-content relative z-10 w-full px-6 pt-6 pb-10 md:px-10 lg:px-14">
        {/* ─── 统计卡片区 ─── */}
        <div className="portrait-history-stats mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard
            icon={FileText}
            label="总就诊次数"
            value={stats.total}
            color="bg-gradient-to-br from-violet-500 to-violet-600"
            delay={0.05}
          />
          <StatCard
            icon={ShieldCheck}
            label="已完成"
            value={stats.completed}
            color="bg-gradient-to-br from-emerald-500 to-emerald-600"
            delay={0.1}
          />
          <StatCard
            icon={CalendarDays}
            label="进行中"
            value={stats.inProgress}
            color="bg-gradient-to-br from-amber-500 to-amber-600"
            delay={0.15}
          />
          <StatCard
            icon={TrendingUp}
            label="平均 PHQ-9"
            value={stats.avgScore}
            color="bg-gradient-to-br from-blue-500 to-blue-600"
            delay={0.2}
          />
        </div>

        {/* ─── 筛选栏 ─── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25 }}
          className="history-filters mb-5 flex items-center gap-3"
        >
          <Filter className="h-4 w-4 text-slate-400" />
          <div className="flex gap-1 rounded-xl bg-white/80 p-1 shadow-sm ring-1 ring-black/[0.04] backdrop-blur-sm">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key)}
                className={`rounded-lg px-4 py-1.5 text-xs font-medium transition-all cursor-pointer ${
                  filter === tab.key
                    ? "bg-gradient-to-r from-violet-500 to-blue-500 text-white shadow-sm"
                    : "text-slate-500 hover:text-slate-700 hover:bg-slate-50"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {filter !== "all" && (
            <span className="text-xs text-slate-400">
              {filtered.length} 条结果
            </span>
          )}
        </motion.div>

        {/* ─── 列表区 ─── */}
        {state.loading && state.encounters.length === 0 ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <SkeletonRow key={i} />
            ))}
          </div>
        ) : filtered.length === 0 && !state.loading ? (
          <EmptyState hasFilter={filter !== "all"} />
        ) : (
          <div className="space-y-3">
            {filtered.map((encounter, index) => (
              <EncounterCard
                key={encounter.id}
                encounter={encounter}
                onContinue={handleContinue}
                onViewDetail={handleViewDetail}
                index={index}
              />
            ))}
          </div>
        )}

        {/* 加载更多 */}
        {state.hasMore && filter === "all" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-6 text-center"
          >
            <button
              onClick={loadMore}
              disabled={state.loading}
              className="inline-flex items-center gap-2 rounded-xl border border-violet-200 bg-white/80 px-6 py-2.5 text-sm font-medium text-violet-600 shadow-sm backdrop-blur-sm transition-all hover:bg-violet-50 disabled:opacity-50 cursor-pointer"
            >
              {state.loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  加载中...
                </>
              ) : (
                "加载更多"
              )}
            </button>
          </motion.div>
        )}

        {/* 错误 */}
        {state.error && <ErrorState error={state.error} onRetry={loadInitial} />}
      </div>

      {/* ─── 续做确认弹窗 ─── */}
      {dialog.open && dialog.encounter && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm"
            onClick={cancelResume}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="history-resume-dialog relative mx-4 w-full max-w-md overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-black/[0.06]"
          >
            <div className="h-1 bg-gradient-to-r from-violet-500 via-blue-500 to-violet-500" />
            <div className="p-6">
              <h2 className="text-lg font-semibold text-slate-900">继续就诊</h2>
              <p className="mt-2 text-sm text-slate-500">
                上次进行到
                <span className="font-medium text-violet-600">
                  {dialog.encounter.current_flow_type === "assessment" ? "量表评估阶段" : "问诊阶段"}
                </span>
                ，是否继续？
              </p>
              <p className="mt-3 rounded-xl bg-violet-50/60 px-4 py-3 text-xs leading-relaxed text-slate-600 ring-1 ring-violet-100">
                {dialog.encounter.chief_complaint_summary || "无主诉摘要"}
              </p>
              {resumeError && (
                <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-600">
                  {resumeError}
                </div>
              )}
              <div className="mt-5 flex justify-end gap-3">
                <button
                  onClick={cancelResume}
                  disabled={isResuming}
                  className="rounded-xl px-5 py-2.5 text-sm text-slate-500 transition-colors hover:text-slate-700 cursor-pointer"
                >
                  取消
                </button>
                <button
                  onClick={() => void confirmResume()}
                  disabled={isResuming}
                  className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-blue-500 px-5 py-2.5 text-sm font-medium text-white shadow-md shadow-violet-500/20 transition-all hover:shadow-lg disabled:opacity-50 cursor-pointer"
                >
                  {isResuming ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      继续中...
                    </>
                  ) : (
                    "继续就诊"
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
