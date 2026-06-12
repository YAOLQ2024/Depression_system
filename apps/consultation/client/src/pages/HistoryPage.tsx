import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { APP_PATHS } from "../routes";
import { EncounterCard } from "../components/EncounterCard";
import { useHistoryList } from "../hooks/useHistoryList";
import { useResumeEncounter } from "../hooks/useResumeEncounter";
import type { EncounterSummary } from "../services/api/contracts";

export default function HistoryPage() {
  const navigate = useNavigate();
  const { state, loadInitial, loadMore } = useHistoryList();
  const { dialog, promptResume, cancelResume, confirmResume } = useResumeEncounter();

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  const handleContinue = (encounter: EncounterSummary) => {
    promptResume(encounter);
  };

  const handleViewDetail = (encounter: EncounterSummary) => {
    navigate(`${APP_PATHS.history}/${encounter.id}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950/20 to-slate-950">
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-semibold text-white">历史就诊记录</h1>
          <button
            onClick={() => navigate(APP_PATHS.home)}
            className="text-sm text-slate-400 hover:text-white transition-colors"
          >
            返回首页
          </button>
        </div>

        {/* 列表 */}
        {state.encounters.length === 0 && !state.loading && (
          <div className="text-center py-16 text-slate-400">
            <p className="text-lg mb-2">暂无就诊记录</p>
            <p className="text-sm">开始一次问诊后，记录会出现在这里</p>
          </div>
        )}

        <div className="space-y-3">
          {state.encounters.map((encounter) => (
            <EncounterCard
              key={encounter.id}
              encounter={encounter}
              onContinue={handleContinue}
              onViewDetail={handleViewDetail}
            />
          ))}
        </div>

        {/* 加载更多 */}
        {state.hasMore && (
          <div className="mt-6 text-center">
            <button
              onClick={loadMore}
              disabled={state.loading}
              className="text-sm text-indigo-400 hover:text-indigo-300 disabled:text-slate-500 transition-colors"
            >
              {state.loading ? "加载中..." : "加载更多..."}
            </button>
          </div>
        )}

        {/* 加载状态 */}
        {state.loading && state.encounters.length === 0 && (
          <div className="text-center py-16 text-slate-400">
            <p>加载中...</p>
          </div>
        )}

        {/* 错误提示 */}
        {state.error && (
          <div className="mt-4 text-center text-red-400 text-sm">{state.error}</div>
        )}
      </div>

      {/* 断点续做确认弹窗 */}
      {dialog.open && dialog.encounter && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-slate-800 rounded-2xl border border-white/10 p-6 max-w-sm w-full mx-4 shadow-2xl">
            <h2 className="text-lg font-medium text-white mb-3">继续就诊</h2>
            <p className="text-sm text-slate-300 mb-1">
              上次进行到
              <span className="text-amber-400 font-medium">
                {dialog.encounter.current_flow_type === "assessment" ? "量表评估阶段" : "问诊阶段"}
              </span>
              ，是否继续？
            </p>
            <p className="text-xs text-slate-500 mb-5">
              {dialog.encounter.chief_complaint_summary || "无主诉摘要"}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={cancelResume}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
              >
                取消
              </button>
              <button
                onClick={confirmResume}
                className="px-4 py-2 text-sm bg-indigo-500 hover:bg-indigo-400 text-white rounded-lg transition-colors"
              >
                继续
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
