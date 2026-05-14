import { ActionButton, SectionHeading, SideCard, SurfaceCard } from "../components/patient-ui";
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
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
      <SurfaceCard className="grid gap-6 p-6 md:p-8">
        <SectionHeading
          action={
            <ActionButton onClick={() => void onRefresh()} variant="secondary">
              刷新结果
            </ActionButton>
          }
          eyebrow="结果分析"
          title="聚合评估结果"
        />

        <div className="grid gap-4 md:grid-cols-3">
          {[
            ["量表完成数", `${completedScaleCount} / ${totalScaleCount}`],
            ["会话状态", assessment.status === "completed" ? "已完成" : assessment.status],
            ["聚合结果", assessment.aggregate_payload ? "已生成" : "待生成"],
          ].map(([label, value]) => (
            <div className="rounded-[24px] border border-white/12 bg-white/8 p-5" key={label}>
              <p className="text-sm text-white/62">{label}</p>
              <p className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">{value}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-4">
          <h3 className="text-xl font-semibold text-white">量表结果摘要</h3>
          <div className="grid gap-4">
            {(assessment.results || []).map((result) => {
              const meta = assessmentCatalog.find((item) => item.slug === result.scale_slug);
              return (
                <div
                  className="flex flex-col gap-4 rounded-[24px] border border-white/12 bg-white/8 p-5 sm:flex-row sm:items-center sm:justify-between"
                  key={`${result.scale_slug}-${result.completed_at}`}
                >
                  <div>
                    <p className="text-lg font-semibold text-white">{meta?.name || result.scale_slug}</p>
                    <p className="mt-2 text-sm text-white/64">{result.interpretation_label || "已完成评估"}</p>
                  </div>
                  <div className="grid gap-1 text-sm font-medium text-white/78 sm:text-right">
                    <span>原始分 {result.raw_score}</span>
                    <span>换算分 {result.derived_score}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="grid gap-4">
          <h3 className="text-xl font-semibold text-white">聚合载荷</h3>
          <pre className="overflow-x-auto rounded-[24px] border border-white/12 bg-white/8 p-5 text-sm leading-7 text-white/80">
            {JSON.stringify(assessment.aggregate_payload || {}, null, 2)}
          </pre>
        </div>
      </SurfaceCard>

      <aside className="grid gap-4">
        <SideCard>
          <p className="text-base font-semibold text-white">结果提示</p>
          <ul className="mt-4 grid gap-3 pl-5 text-sm leading-7 text-white/70">
            <li>聚合结果用于辅助评估，不构成单独医疗诊断。</li>
            <li>请结合后续临床判断与人工复核结果解释本次结论。</li>
            <li>如出现高风险信号，请优先进入人工支持流程。</li>
          </ul>
        </SideCard>
      </aside>
    </section>
  );
}

export default ResultPage;
