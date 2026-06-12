import { useNavigate, useParams } from "react-router-dom";
import { APP_PATHS } from "../routes";
import { useHistoryDetail } from "../hooks/useHistoryDetail";
import { EncounterTimeline } from "../components/EncounterTimeline";
import { cn } from "../lib/utils";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  in_progress: "进行中",
  paused: "已暂停",
  completed: "已完成",
};

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function HistoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { state, reload } = useHistoryDetail(id);

  const encounter = state.encounter;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950/20 to-slate-950">
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* 顶部导航 */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => navigate(APP_PATHS.history)}
            className="text-sm text-slate-400 hover:text-white transition-colors"
          >
            ← 返回历史列表
          </button>
        </div>

        {/* 加载状态 */}
        {state.loading && (
          <div className="text-center py-16 text-slate-400">
            <p>加载中...</p>
          </div>
        )}

        {/* 错误状态 */}
        {state.error && (
          <div className="text-center py-16">
            <p className="text-red-400 text-sm mb-3">{state.error}</p>
            <button
              onClick={reload}
              className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              重试
            </button>
          </div>
        )}

        {/* 详情内容 */}
        {encounter && (
          <div className="space-y-6">
            {/* 就诊信息 */}
            <section className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5">
              <h2 className="text-lg font-medium text-white mb-3">就诊信息</h2>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-slate-500">时间：</span>
                  <span className="text-slate-200">{formatDateTime(encounter.created_at)}</span>
                </div>
                <div>
                  <span className="text-slate-500">状态：</span>
                  <span
                    className={cn(
                      "px-2 py-0.5 rounded-full text-xs",
                      encounter.status === "completed"
                        ? "bg-emerald-500/15 text-emerald-400"
                        : "bg-amber-500/15 text-amber-400",
                    )}
                  >
                    {STATUS_LABELS[encounter.status] || encounter.status}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">医生：</span>
                  <span className="text-slate-200">
                    {encounter.consultation?.assigned_doctor_persona || "—"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">阶段：</span>
                  <span className="text-slate-200">
                    {encounter.current_flow_type === "assessment" ? "量表评估" : "问诊"}
                  </span>
                </div>
              </div>
            </section>

            {/* 就诊时间线 */}
            <section className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5">
              <h2 className="text-lg font-medium text-white mb-4">就诊时间线</h2>
              <EncounterTimeline events={encounter.timeline} />
            </section>

            {/* 问诊摘要 */}
            {encounter.consultation && (
              <section className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5">
                <h2 className="text-lg font-medium text-white mb-3">问诊摘要</h2>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-slate-500">主诉：</span>
                    <span className="text-slate-200">
                      {encounter.consultation.chief_complaint_summary || "暂无摘要"}
                    </span>
                  </div>
                </div>
              </section>
            )}

            {/* 评估结果 */}
            {encounter.assessment_results.length > 0 && (
              <section className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5">
                <h2 className="text-lg font-medium text-white mb-3">评估结果</h2>
                <div className="space-y-3">
                  {encounter.assessment_results.map((result) => (
                    <div
                      key={result.scale_slug}
                      className="flex items-center justify-between p-3 rounded-lg bg-white/5"
                    >
                      <div>
                        <p className="text-sm text-slate-200 font-medium uppercase">
                          {result.scale_slug}
                        </p>
                        <p className="text-xs text-slate-400">
                          {result.interpretation_label || "—"}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-semibold text-white">
                          {result.raw_score}
                          <span className="text-xs text-slate-500 ml-1">分</span>
                        </p>
                        {result.risk_flags && result.risk_flags.length > 0 && (
                          <p className="text-xs text-red-400">
                            {result.risk_flags.length} 个风险标记
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 无评估结果提示 */}
            {encounter.assessment_results.length === 0 && encounter.assessment === null && (
              <section className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5">
                <h2 className="text-lg font-medium text-white mb-3">评估结果</h2>
                <p className="text-sm text-slate-500">本次就诊尚未进入量表评估阶段</p>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
