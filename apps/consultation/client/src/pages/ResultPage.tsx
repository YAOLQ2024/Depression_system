import type { AssessmentCatalogItem, AssessmentSession } from "../types";

type ResultPageProps = {
  assessment: AssessmentSession;
  assessmentCatalog: AssessmentCatalogItem[];
  onRefresh: () => Promise<void>;
};

function ResultPage({ assessment, assessmentCatalog, onRefresh }: ResultPageProps) {
  const totalScaleCount = assessment.selected_scales?.length || 0;
  const completedScaleCount = assessment.results?.length || 0;

  return (
    <section className="result-page">
      <div className="result-main content-card">
        <div className="card-title-row">
          <div>
            <p className="eyebrow">结果分析</p>
            <h2>聚合评估结果</h2>
          </div>
          <button className="ghost-button" onClick={() => void onRefresh()} type="button">
            刷新结果
          </button>
        </div>

        <div className="result-summary-grid">
          <div className="result-summary-card">
            <span>量表完成数</span>
            <strong>
              {completedScaleCount} / {totalScaleCount}
            </strong>
          </div>
          <div className="result-summary-card">
            <span>会话状态</span>
            <strong>{assessment.status === "completed" ? "已完成" : assessment.status}</strong>
          </div>
          <div className="result-summary-card">
            <span>聚合结果</span>
            <strong>{assessment.aggregate_payload ? "已生成" : "待生成"}</strong>
          </div>
        </div>

        <div className="result-section">
          <h3>量表结果摘要</h3>
          <div className="result-scale-list">
            {(assessment.results || []).map((result) => {
              const meta = assessmentCatalog.find((item) => item.slug === result.scale_slug);
              return (
                <div className="result-scale-card" key={`${result.scale_slug}-${result.completed_at}`}>
                  <div>
                    <strong>{meta?.name || result.scale_slug}</strong>
                    <span>{result.interpretation_label || "已完成评估"}</span>
                  </div>
                  <div className="result-scale-metrics">
                    <span>原始分 {result.raw_score}</span>
                    <span>换算分 {result.derived_score}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="result-section">
          <h3>聚合载荷</h3>
          <div className="summary-code-block">
            <pre>{JSON.stringify(assessment.aggregate_payload || {}, null, 2)}</pre>
          </div>
        </div>
      </div>

      <aside className="side-stack">
        <div className="side-card">
          <div className="side-card-header">
            <strong>结果提示</strong>
          </div>
          <ul className="hint-list">
            <li>聚合结果用于辅助评估，不构成单独医疗诊断。</li>
            <li>请结合后续临床判断与人工复核结果解释本次结论。</li>
            <li>如出现高风险信号，请优先进入人工支持流程。</li>
          </ul>
        </div>
      </aside>
    </section>
  );
}

export default ResultPage;
