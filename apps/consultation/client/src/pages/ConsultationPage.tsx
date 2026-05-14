import { Mic, Shield, Video } from "lucide-react";

import {
  ActionButton,
  FormField,
  ProgressSteps,
  SideCard,
  StatusPill,
  SurfaceCard,
  TextArea,
} from "../components/patient-ui";
import type { BootstrapPayload, ConsultationSession } from "../types";
import { CONSULTATION_VISUAL_STEPS, getConsultationStageName, getConsultationVisualStep } from "../workflow";

type ConsultationPageProps = {
  bootstrap: BootstrapPayload | null;
  consultation: ConsultationSession;
  loading: boolean;
  consultationInput: string;
  onConsultationInputChange: (value: string) => void;
  onSubmitTurn: (payload: Record<string, unknown>) => Promise<void>;
  onSubmitManualTurn: () => Promise<void>;
  onRefresh: () => Promise<void>;
  onStartAssessment: () => Promise<void>;
};

function ConsultationPage({
  bootstrap,
  consultation,
  loading,
  consultationInput,
  onConsultationInputChange,
  onSubmitTurn,
  onSubmitManualTurn,
  onRefresh,
  onStartAssessment,
}: ConsultationPageProps) {
  const consultationVisualStep = getConsultationVisualStep(consultation.current_stage_id);

  function findPersonaName(personaId?: string | null) {
    const match = bootstrap?.doctor_personas?.find((item) => item.persona_id === personaId);
    return match?.display_name || "张小雨";
  }

  return (
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
      <SurfaceCard className="grid gap-6 p-5 md:p-6">
        <ProgressSteps currentStep={consultationVisualStep} items={CONSULTATION_VISUAL_STEPS} />

        <div className="grid gap-5 2xl:grid-cols-[minmax(360px,1.08fr)_minmax(340px,0.92fr)]">
          <div className="rounded-[28px] border border-slate-200 bg-white/84 p-4 shadow-[0_16px_36px_rgba(10,18,40,0.08)] backdrop-blur-md">
            <StatusPill tone="positive">AI 数字医生 · 在线</StatusPill>
            <div className="mt-4 flex min-h-[540px] flex-col justify-end rounded-[28px] border border-slate-200 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(228,236,255,0.8)),radial-gradient(circle_at_top,rgba(202,220,255,0.7),transparent_38%),linear-gradient(180deg,rgba(255,255,255,0.58)_0%,rgba(188,205,255,0.4)_100%)] p-6">
              <div className="mx-auto flex h-[320px] w-[240px] items-center justify-center rounded-[140px_140px_100px_100px] bg-[radial-gradient(circle_at_50%_30%,rgba(255,255,255,0.72),rgba(238,245,255,0.34)),linear-gradient(180deg,rgba(255,255,255,0.42),rgba(213,224,255,0.22))] shadow-[inset_0_0_0_12px_rgba(255,255,255,0.16),0_30px_60px_rgba(61,73,180,0.2)]">
                <div className="flex h-[132px] w-[132px] items-center justify-center rounded-full bg-[linear-gradient(135deg,#2563eb,#38bdf8)] text-6xl font-semibold text-white">
                  医
                </div>
              </div>
              <div className="mt-6 rounded-[24px] border border-slate-200 bg-white/88 px-5 py-4 text-[1.05rem] leading-8 text-slate-900 shadow-[0_10px_28px_rgba(10,18,40,0.06)]">
                {consultation.current_prompt || "您好，我将陪您完成本次心理问诊。"}
              </div>
              <div className="mt-3 inline-flex w-fit items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">
                <Mic size={14} />
                语音连接正常
              </div>
            </div>
          </div>

          <div className="rounded-[28px] border border-slate-200 bg-white/84 p-4 shadow-[0_16px_36px_rgba(10,18,40,0.08)] backdrop-blur-md">
            <div className="mb-5 flex flex-wrap gap-2">
              {["问诊对话", "高风险问题排查", "问诊笔记"].map((tab, index) => (
                <button
                  key={tab}
                  className={`rounded-full px-4 py-2.5 text-sm font-medium transition ${
                    index === 0 ? "bg-[#315CFF] text-white shadow-[0_10px_24px_rgba(49,92,255,0.22)]" : "border border-slate-200 bg-slate-50 text-slate-500 hover:border-slate-300 hover:bg-white"
                  }`}
                  type="button"
                >
                  {tab}
                </button>
              ))}
            </div>

            <div className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-[0_10px_28px_rgba(10,18,40,0.05)]">
              <p className="mb-3 text-sm font-semibold text-slate-500">{findPersonaName(consultation.assigned_doctor_persona)}</p>
              <p className="text-lg leading-8 text-slate-900">{consultation.current_prompt || "系统正在准备当前问诊提示。"}</p>
            </div>

            {consultation.status === "handoff_ready" ? (
              <div className="mt-5 rounded-[26px] border border-emerald-200 bg-emerald-50 p-5">
                <h3 className="text-xl font-semibold text-emerald-900">规则问诊已完成</h3>
                <p className="mt-2 text-sm leading-7 text-emerald-800">当前可以进入量表问诊阶段。</p>
                <div className="mt-5">
                  <ActionButton disabled={loading} onClick={() => void onStartAssessment()}>
                    进入量表问诊
                  </ActionButton>
                </div>
              </div>
            ) : consultation.status === "paused_for_human_review" ? (
              <div className="mt-5 rounded-[26px] border border-orange-200 bg-orange-50 p-5">
                <h3 className="text-xl font-semibold text-orange-900">已触发人工复核</h3>
                <p className="mt-2 text-sm leading-7 text-orange-800">系统检测到高风险信号，请转人工支持处理。</p>
              </div>
            ) : (
              <>
                <div className="mt-5">
                  <FormField label="您的回答（按住下方按钮说话）">
                    <TextArea
                      placeholder="如果暂时不接语音，可以直接输入本轮患者回答。"
                      value={consultationInput}
                      onChange={(event) => onConsultationInputChange(event.target.value)}
                    />
                  </FormField>
                </div>

                <div className="mt-5 rounded-[24px] border border-slate-200 bg-slate-50 p-4">
                  <p className="mb-4 text-sm font-semibold text-slate-600">实时语音识别</p>
                  <div className="flex h-14 items-end gap-[5px]">
                    {Array.from({ length: 24 }).map((_, index) => (
                      <span
                        key={index}
                        className="w-[5px] rounded-full bg-[linear-gradient(180deg,rgba(255,255,255,0.7),rgba(146,171,255,0.88))]"
                        style={{ height: `${18 + ((index * 13) % 42)}px` }}
                      />
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <ActionButton disabled variant="secondary">
            暂停问诊
          </ActionButton>
          <ActionButton onClick={() => void onSubmitTurn({ input_type: "continue_button" })} variant="secondary">
            重说上一句
          </ActionButton>
          <button
            className="flex h-24 w-24 items-center justify-center rounded-full bg-[linear-gradient(180deg,#3b82f6,#1d4ed8)] text-sm font-semibold text-white shadow-[0_26px_50px_rgba(37,99,235,0.28)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={loading}
            onClick={() => void onSubmitManualTurn()}
            type="button"
          >
            按住说话
          </button>
          <ActionButton className="min-w-[164px]" disabled={loading} onClick={() => void onSubmitManualTurn()}>
            下一步
          </ActionButton>
        </div>

        <div className="flex flex-wrap justify-end gap-2">
          <ActionButton onClick={() => void onSubmitTurn({ input_type: "silence" })} variant="ghost">
            模拟沉默
          </ActionButton>
          <ActionButton onClick={() => void onSubmitTurn({ input_type: "recognition_failure" })} variant="ghost">
            模拟识别失败
          </ActionButton>
          <ActionButton onClick={() => void onRefresh()} variant="ghost">
            刷新状态
          </ActionButton>
        </div>
      </SurfaceCard>

      <aside className="grid gap-4">
        <SideCard>
          <div className="mb-4 flex items-center justify-between gap-3">
            <strong className="text-base font-semibold text-slate-900">实时监测</strong>
            <StatusPill tone="positive">监测中</StatusPill>
          </div>
          <div className="flex min-h-[188px] items-end justify-center rounded-[24px] border border-slate-200 bg-[radial-gradient(circle_at_top,rgba(207,220,255,0.45),transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.95)_0%,rgba(221,231,255,0.76)_100%)] p-4 text-sm font-semibold text-slate-700">
            <Video size={16} className="mr-2 text-[#315CFF]" />
            用户视频
          </div>
        </SideCard>

        <SideCard>
          <div className="mb-4 flex items-center justify-between gap-3">
            <strong className="text-base font-semibold text-slate-900">会话进度</strong>
            <span className="text-sm text-slate-500">{consultationVisualStep}/6</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-[linear-gradient(90deg,#315CFF,#5B7CFF_52%,#89A1FF)]" style={{ width: `${(consultationVisualStep / 6) * 100}%` }} />
          </div>
          <p className="mt-3 text-sm leading-7 text-slate-600">当前阶段：{getConsultationStageName(consultation.current_stage_id)}</p>
        </SideCard>

        <SideCard>
          <div className="mb-4 flex items-center justify-between gap-3">
            <strong className="text-base font-semibold text-slate-900">情绪状态</strong>
            <StatusPill tone="positive">实时更新</StatusPill>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              ["情绪倾向", consultation.chief_complaint_summary ? "平和" : "待评估"],
              ["焦虑水平", consultation.current_history_structured_result ? "轻度" : "待评估"],
              ["压力指数", consultation.high_risk_screening_result ? "中等" : "待评估"],
              ["疲劳程度", "较低"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm text-slate-500">{label}</p>
                <p className="mt-2 text-base font-semibold text-slate-900">{value}</p>
              </div>
            ))}
          </div>
        </SideCard>

        <SideCard>
          <div className="mb-4 flex items-center justify-between gap-3">
            <strong className="text-base font-semibold text-slate-900">问诊提示</strong>
          </div>
          <ul className="grid gap-3 pl-5 text-sm leading-7 text-slate-600">
            <li>倾听真实感受，如实表达更有助于医生理解您。</li>
            <li>如有不适可随时暂停或结束问诊。</li>
            <li>
              <span className="inline-flex items-center gap-2 text-slate-600">
                <Shield size={14} />
                信息仅用于医疗评估，系统会保护您的隐私与安全。
              </span>
            </li>
          </ul>
        </SideCard>
      </aside>
    </section>
  );
}

export default ConsultationPage;
