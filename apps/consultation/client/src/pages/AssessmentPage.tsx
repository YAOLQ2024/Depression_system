import type { FormEvent } from "react";

import {
  ActionButton,
  FormField,
  ProgressSteps,
  SideCard,
  StatusPill,
  SurfaceCard,
  TextArea,
} from "../components/patient-ui";
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
      { className: "border-sky-200 bg-sky-50 text-slate-900", iconClassName: "bg-sky-100 text-sky-700", icon: "○" },
      { className: "border-emerald-200 bg-emerald-50 text-slate-900", iconClassName: "bg-emerald-100 text-emerald-700", icon: "◐" },
      { className: "border-amber-200 bg-amber-50 text-slate-900", iconClassName: "bg-amber-100 text-amber-700", icon: "◑" },
      { className: "border-rose-200 bg-rose-50 text-slate-900", iconClassName: "bg-rose-100 text-rose-700", icon: "●" },
    ];

    return palette[index] || palette[Math.min(score, palette.length - 1)];
  }

  return (
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
      <SurfaceCard className="grid gap-6 p-5 md:p-6">
        <ProgressSteps items={(assessment.selected_scales || []).map((slug) => assessmentCatalog.find((item) => item.slug === slug)?.short_name || slug)} currentStep={Math.max(completedScaleCount + 1, 1)} />

        <div className="rounded-[28px] border border-slate-200 bg-white/88 p-5 shadow-[0_16px_36px_rgba(10,18,40,0.08)] backdrop-blur-md">
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm font-medium text-slate-600">
            <span>
              第 <strong>{assessment.current_item?.index || 0}</strong> / {currentScaleMeta?.item_count || 0} 题
            </span>
            <span>
              {currentScaleMeta?.item_count
                ? `${Math.round(((assessment.current_item?.index || 0) / currentScaleMeta.item_count) * 100)}%`
                : "0%"}
            </span>
          </div>

          <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-[linear-gradient(90deg,#315CFF,#5B7CFF_52%,#89A1FF)]"
              style={{
                width: currentScaleMeta?.item_count
                  ? `${((assessment.current_item?.index || 0) / currentScaleMeta.item_count) * 100}%`
                  : "0%",
              }}
            />
          </div>

          <h2 className="mt-6 text-[1.85rem] font-semibold leading-[1.5] tracking-[-0.04em] text-slate-950">
            {assessment.current_item?.text || "量表已完成"}
          </h2>

          <form className="mt-6 grid gap-6" onSubmit={onSubmit}>
            <div className="grid gap-4 lg:grid-cols-2">
              {(assessment.current_item?.answer_options || []).map((option, index) => {
                const tone = getAssessmentOptionTone(option.score, index);
                const selected = selectedAssessmentScore === option.score;

                return (
                  <button
                    key={`${assessment.current_item?.item_id}-${option.score}`}
                  className={`flex items-center gap-4 rounded-[24px] border p-5 text-left transition ${
                    selected
                        ? "border-[#8EA8FF] bg-[#EDF2FF] shadow-[0_18px_36px_rgba(83,94,202,0.12)]"
                        : `${tone.className} hover:border-slate-300 hover:bg-white`
                    }`}
                    onClick={() => onSelectAssessmentScore(option.score)}
                    type="button"
                  >
                    <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-lg font-semibold ${selected ? "bg-[#315CFF] text-white" : tone.iconClassName}`}>
                      {tone.icon}
                    </div>
                    <div>
                      <p className="text-base font-semibold text-slate-900">{option.label}</p>
                      <p className="mt-1 text-sm text-slate-500">分值 {option.score}</p>
                    </div>
                  </button>
                );
              })}
            </div>

            <FormField label="语音/文本原始输入兜底">
              <TextArea
                placeholder="后续接正式语音答案时，这里用于保存原始文本。"
                value={assessmentRawInput}
                onChange={(event) => onAssessmentRawInputChange(event.target.value)}
              />
            </FormField>

            <div className="flex flex-wrap items-center gap-4">
              <ActionButton disabled variant="secondary">
                上一题
              </ActionButton>
              <ActionButton onClick={() => void onRefresh()} variant="secondary">
                刷新状态
              </ActionButton>
              <span className="text-sm font-medium text-slate-500">按住说话回答</span>
              <ActionButton className="min-w-[164px]" disabled={loading || selectedAssessmentScore === null} type="submit">
                下一题
              </ActionButton>
            </div>
          </form>
        </div>
      </SurfaceCard>

      <aside className="grid gap-4">
        <SideCard>
          <div className="mb-4 flex items-center justify-between gap-3">
            <strong className="text-base font-semibold text-slate-900">实时视频</strong>
            <StatusPill tone="positive">连接正常</StatusPill>
          </div>
          <div className="flex min-h-[204px] items-end justify-center rounded-[24px] border border-slate-200 bg-[radial-gradient(circle_at_top,rgba(207,220,255,0.45),transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.95)_0%,rgba(221,231,255,0.76)_100%)] p-4 text-sm font-semibold text-slate-700">
            用户视频
          </div>
        </SideCard>

        <SideCard>
          <div className="mb-4 flex items-center justify-between gap-3">
            <strong className="text-base font-semibold text-slate-900">多模态数据采集</strong>
            <StatusPill tone="positive">实时采集中</StatusPill>
          </div>
          <div className="grid gap-3">
            {[
              ["表情", "正常"],
              ["姿态", "正常"],
              ["语音", "正常"],
              ["脑电", "良好"],
              ["文本", "分析中"],
            ].map(([label, status]) => (
              <div className="flex items-center justify-between gap-3 border-b border-slate-200 pb-3 last:border-b-0 last:pb-0" key={label}>
                <span className="text-sm text-slate-500">{label}</span>
                <strong className="text-sm font-semibold text-slate-900">{status}</strong>
              </div>
            ))}
          </div>
        </SideCard>

        <div className="grid gap-3">
          {[
            ["当前状态", completedScaleCount > 0 ? "持续评估中" : "开始评估"],
            ["问诊用时", `${completedScaleCount + 6}:2${completedScaleCount}`],
            ["隐私与安全", "已保护"],
          ].map(([label, value]) => (
            <SideCard key={label}>
              <p className="text-sm text-slate-500">{label}</p>
              <p className="mt-2 text-lg font-semibold text-slate-900">{value}</p>
            </SideCard>
          ))}
        </div>
      </aside>
    </section>
  );
}

export default AssessmentPage;
