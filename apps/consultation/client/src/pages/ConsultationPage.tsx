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
    <section className="consultation-page">
      <div className="consultation-main content-card">
        <div className="consultation-stepper">
          {CONSULTATION_VISUAL_STEPS.map((step, index) => (
            <div
              key={step}
              className={`consultation-step ${consultationVisualStep === index + 1 ? "active" : ""} ${consultationVisualStep > index + 1 ? "done" : ""}`}
            >
              <div className="consultation-step-index">{index + 1}</div>
              <span>{step}</span>
            </div>
          ))}
        </div>

        <div className="consultation-grid">
          <div className="doctor-stage">
            <div className="doctor-stage-label">AI 数字医生 · 在线</div>
            <div className="doctor-canvas">
              <div className="doctor-portrait">
                <div className="doctor-face">医</div>
              </div>
              <div className="doctor-caption">{consultation.current_prompt || "您好，我将陪您完成本次心理问诊。"}</div>
            </div>
            <div className="doctor-footer">语音连接正常</div>
          </div>

          <div className="dialogue-stage">
            <div className="tab-row">
              <button className="active" type="button">
                问诊对话
              </button>
              <button type="button">高风险问题排查</button>
              <button type="button">问诊笔记</button>
            </div>

            <div className="chat-bubble">
              <strong>{findPersonaName(consultation.assigned_doctor_persona)}</strong>
              <p>{consultation.current_prompt || "系统正在准备当前问诊提示。"}</p>
            </div>

            {consultation.status === "handoff_ready" ? (
              <div className="handoff-card">
                <h3>规则问诊已完成</h3>
                <p>当前可以进入量表问诊阶段。</p>
                <button className="primary-button" disabled={loading} onClick={() => void onStartAssessment()} type="button">
                  进入量表问诊
                </button>
              </div>
            ) : consultation.status === "paused_for_human_review" ? (
              <div className="handoff-card warning">
                <h3>已触发人工复核</h3>
                <p>系统检测到高风险信号，请转人工支持处理。</p>
              </div>
            ) : (
              <>
                <div className="answer-area">
                  <label>
                    您的回答（按住下方按钮说话）
                    <textarea
                      value={consultationInput}
                      onChange={(event) => onConsultationInputChange(event.target.value)}
                      placeholder="如果暂时不接语音，可以直接输入本轮患者回答。"
                    />
                  </label>
                </div>

                <div className="wave-row">
                  <div className="wave-label">实时语音识别</div>
                  <div className="wave-bars">
                    {Array.from({ length: 24 }).map((_, index) => (
                      <span key={index} style={{ height: `${18 + ((index * 13) % 42)}px` }} />
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="consultation-bottom">
          <button className="ghost-button" disabled type="button">
            暂停问诊
          </button>
          <button className="ghost-button" onClick={() => void onSubmitTurn({ input_type: "continue_button" })} type="button">
            重说上一句
          </button>
          <button className="mic-button" disabled={loading} onClick={() => void onSubmitManualTurn()} type="button">
            按住说话
          </button>
          <button className="primary-button next-button" disabled={loading} onClick={() => void onSubmitManualTurn()} type="button">
            下一步
          </button>
        </div>

        <div className="assist-actions">
          <button className="text-button" onClick={() => void onSubmitTurn({ input_type: "silence" })} type="button">
            模拟沉默
          </button>
          <button className="text-button" onClick={() => void onSubmitTurn({ input_type: "recognition_failure" })} type="button">
            模拟识别失败
          </button>
          <button className="text-button" onClick={() => void onRefresh()} type="button">
            刷新状态
          </button>
        </div>
      </div>

      <aside className="side-stack">
        <div className="side-card">
          <div className="side-card-header">
            <strong>实时监测</strong>
            <span className="dot-status positive">监测中</span>
          </div>
          <div className="video-placeholder monitor-video">用户视频</div>
        </div>

        <div className="side-card">
          <div className="side-card-header">
            <strong>会话进度</strong>
            <span>{consultationVisualStep}/6</span>
          </div>
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${(consultationVisualStep / 6) * 100}%` }} />
          </div>
          <p className="side-description">当前阶段：{getConsultationStageName(consultation.current_stage_id)}</p>
        </div>

        <div className="side-card">
          <div className="side-card-header">
            <strong>情绪状态</strong>
            <span className="dot-status positive">实时更新</span>
          </div>
          <div className="emotion-grid">
            <div className="emotion-card">
              <span>情绪倾向</span>
              <strong>{consultation.chief_complaint_summary ? "平和" : "待评估"}</strong>
            </div>
            <div className="emotion-card">
              <span>焦虑水平</span>
              <strong>{consultation.current_history_structured_result ? "轻度" : "待评估"}</strong>
            </div>
            <div className="emotion-card">
              <span>压力指数</span>
              <strong>{consultation.high_risk_screening_result ? "中等" : "待评估"}</strong>
            </div>
            <div className="emotion-card">
              <span>疲劳程度</span>
              <strong>较低</strong>
            </div>
          </div>
        </div>

        <div className="side-card">
          <div className="side-card-header">
            <strong>问诊提示</strong>
          </div>
          <ul className="hint-list">
            <li>倾听真实感受，如实表达更有助于医生理解您。</li>
            <li>如有不适可随时暂停或结束问诊。</li>
            <li>信息仅用于医疗评估，系统会保护您的隐私与安全。</li>
          </ul>
        </div>
      </aside>
    </section>
  );
}

export default ConsultationPage;
