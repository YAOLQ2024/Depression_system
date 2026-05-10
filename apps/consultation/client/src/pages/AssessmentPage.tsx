import type { FormEvent } from "react";

import type { AssessmentCatalogItem, AssessmentSession } from "../types";

type AssessmentPageProps = {
  assessment: AssessmentSession;
  assessmentCatalog: AssessmentCatalogItem[];
  loading: boolean;
  assessmentRawInput: string;
  selectedAssessmentScore: number | null;
  onAssessmentRawInputChange: (value: string) => void;
  onSelectAssessmentScore: (score: number) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onRefresh: () => Promise<void>;
};

function AssessmentPage({
  assessment,
  assessmentCatalog,
  loading,
  assessmentRawInput,
  selectedAssessmentScore,
  onAssessmentRawInputChange,
  onSelectAssessmentScore,
  onSubmit,
  onRefresh,
}: AssessmentPageProps) {
  const currentScaleMeta = assessmentCatalog.find((item) => item.slug === assessment.current_scale_slug) || null;
  const completedScaleCount = assessment.results?.length || 0;

  function getAssessmentOptionTone(score: number, index: number) {
    const palette = [
      { className: "tone-calm", icon: "○" },
      { className: "tone-light", icon: "◐" },
      { className: "tone-mid", icon: "◑" },
      { className: "tone-strong", icon: "●" },
    ];

    return palette[index] || palette[Math.min(score, palette.length - 1)];
  }

  return (
    <section className="assessment-page">
      <div className="assessment-main content-card">
        <div className="scale-stepper">
          {(assessment.selected_scales || []).map((slug, index) => {
            const meta = assessmentCatalog.find((item) => item.slug === slug);
            const isDone = (assessment.results || []).some((result) => result.scale_slug === slug);
            const isCurrent =
              assessment.current_scale_slug === slug ||
              (!assessment.current_scale_slug && isDone && index === (assessment.selected_scales || []).length - 1);

            return (
              <div key={slug} className={`scale-step ${isDone ? "done" : ""} ${isCurrent ? "active" : ""}`}>
                <div className="scale-step-index">{index + 1}</div>
                <span>{meta?.short_name || slug}</span>
              </div>
            );
          })}
        </div>

        <div className="assessment-panel">
          <div className="assessment-progress">
            <span>
              第 <strong>{assessment.current_item?.index || 0}</strong> / {currentScaleMeta?.item_count || 0} 题
            </span>
            <span>
              {currentScaleMeta?.item_count
                ? `${Math.round(((assessment.current_item?.index || 0) / currentScaleMeta.item_count) * 100)}%`
                : "0%"}
            </span>
          </div>

          <div className="progress-bar">
            <div
              className="progress-bar-fill"
              style={{
                width: currentScaleMeta?.item_count
                  ? `${((assessment.current_item?.index || 0) / currentScaleMeta.item_count) * 100}%`
                  : "0%",
              }}
            />
          </div>

          <h2>{assessment.current_item?.text || "量表已完成"}</h2>

          <form className="assessment-form" onSubmit={onSubmit}>
            <div className="answer-grid">
              {(assessment.current_item?.answer_options || []).map((option, index) => {
                const tone = getAssessmentOptionTone(option.score, index);
                return (
                  <button
                    key={`${assessment.current_item?.item_id}-${option.score}`}
                    className={`answer-card ${tone.className} ${selectedAssessmentScore === option.score ? "selected" : ""}`}
                    onClick={() => onSelectAssessmentScore(option.score)}
                    type="button"
                  >
                    <div className={`answer-card-icon ${tone.className}`}>{tone.icon}</div>
                    <div>
                      <strong>{option.label}</strong>
                      <span>分值 {option.score}</span>
                    </div>
                  </button>
                );
              })}
            </div>

            <label className="full-width">
              语音/文本原始输入兜底
              <textarea
                value={assessmentRawInput}
                onChange={(event) => onAssessmentRawInputChange(event.target.value)}
                placeholder="后续接正式语音答案时，这里用于保存原始文本。"
              />
            </label>

            <div className="bottom-action-row">
              <button className="ghost-button disabled" disabled type="button">
                上一题
              </button>
              <button className="ghost-button" onClick={() => void onRefresh()} type="button">
                刷新状态
              </button>
              <div className="voice-hint">按住说话回答</div>
              <button className="primary-button next-button" disabled={loading || selectedAssessmentScore === null} type="submit">
                下一题
              </button>
            </div>
          </form>
        </div>
      </div>

      <aside className="side-stack">
        <div className="side-card">
          <div className="side-card-header">
            <strong>实时视频</strong>
            <span className="dot-status positive">连接正常</span>
          </div>
          <div className="video-placeholder user-video">用户视频</div>
        </div>

        <div className="side-card">
          <div className="side-card-header">
            <strong>多模态数据采集</strong>
            <span className="dot-status positive">实时采集中</span>
          </div>
          <div className="metric-list">
            {[
              ["表情", "正常"],
              ["姿态", "正常"],
              ["语音", "正常"],
              ["脑电", "良好"],
              ["文本", "分析中"],
            ].map(([label, status]) => (
              <div className="metric-row" key={label}>
                <span>{label}</span>
                <strong>{status}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="status-grid">
          <div className="mini-card">
            <span>当前状态</span>
            <strong>{completedScaleCount > 0 ? "持续评估中" : "开始评估"}</strong>
          </div>
          <div className="mini-card">
            <span>问诊用时</span>
            <strong>{`${completedScaleCount + 6}:2${completedScaleCount}`}</strong>
          </div>
          <div className="mini-card">
            <span>隐私与安全</span>
            <strong>已保护</strong>
          </div>
        </div>
      </aside>
    </section>
  );
}

export default AssessmentPage;
