import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiRequest, clearSessionToken, setSessionToken } from "./api";
import type {
  AssessmentCatalogItem,
  AssessmentSession,
  BootstrapPayload,
  ConsultationSession,
  UserRecord,
} from "./types";

const CONSULTATION_VISUAL_STEPS = [
  "主诉采集",
  "现病史",
  "睡眠饮食",
  "情绪体验",
  "高风险筛查",
  "总结建议",
];

const CONSULTATION_STAGE_MAP: Record<string, number> = {
  "stage-01-greeting-and-briefing": 1,
  "stage-02-chief-complaint": 1,
  "stage-03-current-history-followup": 2,
  "stage-04-high-risk-screening": 5,
  "handoff-to-scale-assessment": 6,
};

const PREP_TITLES = ["问诊准备", "数字人问诊", "量表问诊", "结果分析"];

function App() {
  const [user, setUser] = useState<UserRecord | null>(null);
  const [bootstrap, setBootstrap] = useState<BootstrapPayload | null>(null);
  const [consultation, setConsultation] = useState<ConsultationSession | null>(null);
  const [assessment, setAssessment] = useState<AssessmentSession | null>(null);
  const [assessmentCatalog, setAssessmentCatalog] = useState<AssessmentCatalogItem[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [keepLoggedIn, setKeepLoggedIn] = useState(true);
  const [consultationInput, setConsultationInput] = useState("");
  const [assessmentRawInput, setAssessmentRawInput] = useState("");
  const [selectedAssessmentScore, setSelectedAssessmentScore] = useState<number | null>(null);

  useEffect(() => {
    void init();
  }, []);

  useEffect(() => {
    setSelectedAssessmentScore(null);
    setAssessmentRawInput("");
  }, [assessment?.current_item?.item_id]);

  const currentSidebarStep = useMemo(() => {
    if (!user || user.profile_status !== "completed") {
      return 0;
    }
    if (assessment) {
      return 2;
    }
    if (consultation) {
      return 1;
    }
    return 0;
  }, [assessment, consultation, user]);

  const consultationVisualStep = consultation?.current_stage_id
    ? CONSULTATION_STAGE_MAP[consultation.current_stage_id] || 1
    : 1;

  const currentScaleMeta = assessmentCatalog.find((item) => item.slug === assessment?.current_scale_slug) || null;
  const completedScaleCount = assessment?.results?.length || 0;
  const totalScaleCount = assessment?.selected_scales?.length || 0;

  function getSessionStorageKey(userId?: string | null) {
    return userId ? `mcs_consultation_session:${userId}` : null;
  }

  function getAssessmentStorageKey(userId?: string | null) {
    return userId ? `mcs_assessment_session:${userId}` : null;
  }

  function saveConsultationSessionId(sessionId: string, userId?: string | null) {
    const key = getSessionStorageKey(userId || user?.id);
    if (key) {
      window.localStorage.setItem(key, sessionId);
    }
  }

  function readConsultationSessionId(userId?: string | null) {
    const key = getSessionStorageKey(userId || user?.id);
    return key ? window.localStorage.getItem(key) : null;
  }

  function clearConsultationSessionId(userId?: string | null) {
    const key = getSessionStorageKey(userId || user?.id);
    if (key) {
      window.localStorage.removeItem(key);
    }
  }

  function saveAssessmentSessionId(sessionId: string, userId?: string | null) {
    const key = getAssessmentStorageKey(userId || user?.id);
    if (key) {
      window.localStorage.setItem(key, sessionId);
    }
  }

  function readAssessmentSessionId(userId?: string | null) {
    const key = getAssessmentStorageKey(userId || user?.id);
    return key ? window.localStorage.getItem(key) : null;
  }

  function clearAssessmentSessionId(userId?: string | null) {
    const key = getAssessmentStorageKey(userId || user?.id);
    if (key) {
      window.localStorage.removeItem(key);
    }
  }

  function resetFeedback() {
    setMessage("");
    setError("");
  }

  async function fetchCurrentUser(): Promise<UserRecord | null> {
    try {
      const data = await apiRequest<{ user: UserRecord }>("/users/me", { method: "GET" });
      return data.user;
    } catch {
      return null;
    }
  }

  async function fetchBootstrap(): Promise<BootstrapPayload> {
    return apiRequest<BootstrapPayload>("/system/bootstrap", { method: "GET" });
  }

  async function fetchAssessmentCatalog(): Promise<AssessmentCatalogItem[]> {
    const data = await apiRequest<{ catalog: AssessmentCatalogItem[] }>("/assessment/catalog", { method: "GET" });
    return data.catalog || [];
  }

  async function fetchExistingConsultation(currentUserId: string) {
    const sessionId = readConsultationSessionId(currentUserId);
    if (!sessionId) {
      return null;
    }
    try {
      const data = await apiRequest<{ consultation: ConsultationSession }>(`/consultations/${sessionId}`, {
        method: "GET",
      });
      return data.consultation;
    } catch {
      clearConsultationSessionId(currentUserId);
      return null;
    }
  }

  async function fetchExistingAssessment(currentUserId: string) {
    const sessionId = readAssessmentSessionId(currentUserId);
    if (!sessionId) {
      return null;
    }
    try {
      const data = await apiRequest<{ assessment_session: AssessmentSession }>(`/assessment/sessions/${sessionId}`, {
        method: "GET",
      });
      return data.assessment_session;
    } catch {
      clearAssessmentSessionId(currentUserId);
      return null;
    }
  }

  async function hydrateAuthenticatedState(currentUser: UserRecord) {
    setUser(currentUser);
    const [bootstrapData, catalogData] = await Promise.all([fetchBootstrap(), fetchAssessmentCatalog()]);
    setBootstrap(bootstrapData);
    setAssessmentCatalog(catalogData);

    if (currentUser.profile_status === "completed") {
      const existingConsultation = await fetchExistingConsultation(currentUser.id);
      setConsultation(existingConsultation);
      if (existingConsultation?.status === "handoff_ready") {
        const existingAssessment = await fetchExistingAssessment(currentUser.id);
        setAssessment(existingAssessment);
      } else {
        clearAssessmentSessionId(currentUser.id);
        setAssessment(null);
      }
    } else {
      clearConsultationSessionId(currentUser.id);
      clearAssessmentSessionId(currentUser.id);
      setConsultation(null);
      setAssessment(null);
    }
  }

  async function bootstrapAuthenticatedState() {
    const currentUser = await fetchCurrentUser();
    setUser(currentUser);
    if (!currentUser) {
      setBootstrap(null);
      setConsultation(null);
      setAssessment(null);
      setAssessmentCatalog([]);
      return;
    }
    await hydrateAuthenticatedState(currentUser);
  }

  async function init() {
    resetFeedback();
    try {
      await bootstrapAuthenticatedState();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "初始化失败");
    }
  }

  function findPersonaName(personaId?: string | null) {
    const match = bootstrap?.doctor_personas?.find((item) => item.persona_id === personaId);
    return match?.display_name || "张小雨";
  }

  function getConsultationStageName() {
    const stageNameMap: Record<string, string> = {
      "stage-01-greeting-and-briefing": "初始问候与流程说明",
      "stage-02-chief-complaint": "主诉采集",
      "stage-03-current-history-followup": "现病史规则式问诊",
      "stage-04-high-risk-screening": "高风险问题排查",
      "handoff-to-scale-assessment": "量表移交",
    };
    return consultation?.current_stage_id ? stageNameMap[consultation.current_stage_id] || consultation.current_stage_id : "数字人问诊";
  }

  function getAssessmentOptionTone(score: number, index: number) {
    const palette = [
      { className: "tone-calm", icon: "○" },
      { className: "tone-light", icon: "◐" },
      { className: "tone-mid", icon: "◑" },
      { className: "tone-strong", icon: "●" },
    ];
    return palette[index] || palette[Math.min(score, palette.length - 1)];
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();
    const formData = new FormData(event.currentTarget);
    try {
      const loginData = await apiRequest<{ user: UserRecord; session_token?: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: formData.get("email"),
          password: formData.get("password"),
        }),
      });
      if (loginData.session_token) {
        setSessionToken(loginData.session_token);
      }
      await new Promise((resolve) => window.setTimeout(resolve, 120));
      await hydrateAuthenticatedState(loginData.user);
      setMessage("登录成功。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "登录失败");
    }
  }

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();
    const formData = new FormData(event.currentTarget);
    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: formData.get("full_name"),
          email: formData.get("email"),
          password: formData.get("password"),
        }),
      });
      setAuthMode("login");
      setMessage("注册成功，请使用新账号登录。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "注册失败");
    }
  }

  async function handlePreparationSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();
    setLoading(true);
    const formData = new FormData(event.currentTarget);
    const payload = Object.fromEntries(formData.entries()) as Record<string, unknown>;
    ["age", "height_cm", "weight_kg"].forEach((field) => {
      const value = payload[field];
      if (value === "") {
        delete payload[field];
      } else if (typeof value === "string") {
        payload[field] = Number(value);
      }
    });
    try {
      const data = await apiRequest<{ user: UserRecord }>("/users/me/profile", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      setUser(data.user);
      setConsultation(null);
      setAssessment(null);
      clearConsultationSessionId();
      clearAssessmentSessionId();
      setBootstrap(await fetchBootstrap());
      setAssessmentCatalog(await fetchAssessmentCatalog());
      setMessage("问诊准备信息已保存，可以进入正式问诊。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "资料保存失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleStartConsultation() {
    resetFeedback();
    setLoading(true);
    try {
      const created = await apiRequest<{ consultation: ConsultationSession }>("/consultations", {
        method: "POST",
        body: JSON.stringify({}),
      });
      saveConsultationSessionId(created.consultation.session_id);
      const started = await apiRequest<{ consultation: ConsultationSession }>(
        `/consultations/${created.consultation.session_id}/start`,
        {
          method: "POST",
          body: JSON.stringify({}),
        },
      );
      setConsultation(started.consultation);
      setMessage("正式问诊已开始。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建问诊失败");
    } finally {
      setLoading(false);
    }
  }

  async function submitConsultationTurn(payload: Record<string, unknown>) {
    if (!consultation) {
      return;
    }
    resetFeedback();
    setLoading(true);
    try {
      const data = await apiRequest<{ consultation: ConsultationSession }>(
        `/consultations/${consultation.session_id}/turns`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      );
      setConsultation(data.consultation);
      if (data.consultation.status === "handoff_ready") {
        setMessage("规则问诊已完成，当前可以进入量表问诊。");
      } else if (data.consultation.status === "paused_for_human_review") {
        setError("系统已触发高风险人工复核，标准问诊主链已暂停。");
      } else {
        setMessage("本轮输入已提交。");
      }
      setConsultationInput("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "提交失败");
    } finally {
      setLoading(false);
    }
  }

  async function submitManualConsultationTurn() {
    const normalized = consultationInput.trim();
    if (!normalized) {
      setError("请先输入本轮患者回答。");
      return;
    }
    await submitConsultationTurn({
      input_type: "manual_input",
      raw_input: normalized,
      transcript_text: normalized,
    });
  }

  async function refreshConsultation() {
    if (!consultation) {
      return;
    }
    resetFeedback();
    setLoading(true);
    try {
      const data = await apiRequest<{ consultation: ConsultationSession }>(`/consultations/${consultation.session_id}`, {
        method: "GET",
      });
      setConsultation(data.consultation);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "刷新失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleStartAssessment() {
    if (!consultation) {
      return;
    }
    resetFeedback();
    setLoading(true);
    try {
      const data = await apiRequest<{ assessment_session: AssessmentSession }>("/assessment/sessions", {
        method: "POST",
        body: JSON.stringify({
          consultation_session_id: consultation.session_id,
          scale_handoff_payload: consultation.scale_handoff_payload || {},
        }),
      });
      setAssessment(data.assessment_session);
      saveAssessmentSessionId(data.assessment_session.session_id);
      setMessage("量表问诊已开始。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建量表会话失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmitAssessment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!assessment || selectedAssessmentScore === null) {
      setError("请先选择本题答案。");
      return;
    }
    resetFeedback();
    setLoading(true);
    try {
      const data = await apiRequest<{ assessment_session: AssessmentSession }>(
        `/assessment/sessions/${assessment.session_id}/answers`,
        {
          method: "POST",
          body: JSON.stringify({
            item_id: assessment.current_item?.item_id,
            selected_option_score: selectedAssessmentScore,
            raw_input: assessmentRawInput || null,
          }),
        },
      );
      setAssessment(data.assessment_session);
      saveAssessmentSessionId(data.assessment_session.session_id);
      if (data.assessment_session.status === "completed") {
        setMessage("量表阶段已完成，已生成聚合结果。");
      } else {
        setMessage("本题答案已提交。");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "提交量表答案失败");
    } finally {
      setLoading(false);
    }
  }

  async function refreshAssessment() {
    if (!assessment) {
      return;
    }
    resetFeedback();
    setLoading(true);
    try {
      const data = await apiRequest<{ assessment_session: AssessmentSession }>(
        `/assessment/sessions/${assessment.session_id}`,
        {
          method: "GET",
        },
      );
      setAssessment(data.assessment_session);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "刷新量表失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    try {
      await apiRequest("/auth/logout", { method: "POST" });
    } catch {
      // ignore
    }
    clearSessionToken();
    clearConsultationSessionId();
    clearAssessmentSessionId();
    setUser(null);
    setBootstrap(null);
    setConsultation(null);
    setAssessment(null);
    setMessage("已退出。");
    setError("");
  }

  function renderTopFeedback() {
    return (
      <>
        {message ? <div className="feedback-banner success">{message}</div> : null}
        {error ? <div className="feedback-banner error">{error}</div> : null}
      </>
    );
  }

  if (!user) {
    return (
      <div className="auth-page">
        <div className="auth-hero">
          <div className="auth-logo">SDS</div>
          <div>
            <h1>SDS 抑郁自评与辅助分析系统</h1>
            <p>3-5 分钟完成自评，生成可解释的结果与建议。</p>
          </div>
          <div className="auth-benefits">
            <div>快速完成测评并查看报告，支持多维度分析</div>
            <div>支持历史记录与趋势对比，追踪心理健康状态</div>
            <div>可选采集表情、语音、EEG，用于辅助分析（不影响问卷提交）</div>
          </div>
          <p className="auth-disclaimer">自评与辅助分析仅供参考，不构成医疗诊断。</p>
          <div className="auth-note-row">
            <span>隐私说明</span>
            <span>数据采集说明（摄像头/麦克风/EEG）</span>
          </div>
        </div>
        <div className="auth-card">
          <div className="auth-card-header">
            <div>
              <p className="eyebrow">欢迎使用</p>
              <h2>{authMode === "login" ? "登录" : "创建账号"}</h2>
              <p className="auth-card-copy">
                {authMode === "login" ? "使用账号登录以继续。" : "先创建账号，再进入患者侧主流程。"}
              </p>
            </div>
            <div className="auth-tabs">
              <button
                className={authMode === "login" ? "active" : ""}
                onClick={() => setAuthMode("login")}
                type="button"
              >
                登录
              </button>
              <button
                className={authMode === "register" ? "active" : ""}
                onClick={() => setAuthMode("register")}
                type="button"
              >
                注册
              </button>
            </div>
          </div>
          {renderTopFeedback()}
          {authMode === "login" ? (
            <form className="auth-form" onSubmit={handleLogin}>
              <label>
                账号
                <input name="email" type="email" defaultValue="participant@mcs.local" placeholder="请输入邮箱账号" />
              </label>
              <label>
                密码
                <div className="password-field">
                  <input
                    name="password"
                    type={passwordVisible ? "text" : "password"}
                    defaultValue="Participant123!"
                    placeholder="请输入密码"
                  />
                  <button
                    className="password-toggle"
                    onClick={() => setPasswordVisible((current) => !current)}
                    type="button"
                  >
                    {passwordVisible ? "隐藏" : "显示"}
                  </button>
                </div>
              </label>
              <div className="auth-inline-row">
                <label className="checkbox-row">
                  <input
                    checked={keepLoggedIn}
                    onChange={(event) => setKeepLoggedIn(event.target.checked)}
                    type="checkbox"
                  />
                  <span>保持登录</span>
                </label>
                <button className="text-link-button" type="button">
                  忘记密码？
                </button>
              </div>
              <button className="primary-button" type="submit">
                登录
              </button>
            </form>
          ) : (
            <form className="auth-form" onSubmit={handleRegister}>
              <label>
                姓名
                <input name="full_name" type="text" />
              </label>
              <label>
                邮箱
                <input name="email" type="email" placeholder="请输入邮箱账号" />
              </label>
              <label>
                密码
                <div className="password-field">
                  <input
                    name="password"
                    type={passwordVisible ? "text" : "password"}
                    placeholder="请设置登录密码"
                  />
                  <button
                    className="password-toggle"
                    onClick={() => setPasswordVisible((current) => !current)}
                    type="button"
                  >
                    {passwordVisible ? "隐藏" : "显示"}
                  </button>
                </div>
              </label>
              <button className="primary-button" type="submit">
                创建账号
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  const profile = user.profile || {};
  const pageTitle = assessment
    ? `${currentScaleMeta?.short_name || assessment.current_scale_slug || "量表"} 量表问诊`
    : consultation
      ? "数字人问诊"
      : user.profile_status !== "completed"
        ? "问诊准备"
        : "正式问诊入口";

  return (
    <div className="consultation-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-logo">♡</div>
          <div>
            <strong>抑郁症辅助问诊系统</strong>
          </div>
        </div>
        <nav className="sidebar-nav">
          {PREP_TITLES.map((title, index) => (
            <div key={title} className={`sidebar-item ${currentSidebarStep === index ? "active" : ""}`}>
              <div className="sidebar-icon">{index + 1}</div>
              <div>
                <strong>{title}</strong>
                <span>
                  {index === 0
                    ? "填写基本信息"
                    : index === 1
                      ? "AI 数字人沟通"
                      : index === 2
                        ? "心理量表评估"
                        : "评估结果与建议"}
                </span>
              </div>
            </div>
          ))}
        </nav>
        <div className="sidebar-help">使用指南</div>
      </aside>

      <main className="main-area">
        <header className="main-header">
          <div>
            <h1>{pageTitle}</h1>
            <p className="breadcrumb">
              {assessment ? `${currentScaleMeta?.name || "量表问诊"}` : consultation ? `AI 数字医生交互` : `患者端主链`}
            </p>
          </div>
          <div className="header-actions">
            <div className="safety-chip">医疗级数据安全保护中</div>
            <div className="user-chip">
              <div className="avatar-circle">{user.full_name.slice(0, 1)}</div>
              <div>
                <strong>{user.full_name}</strong>
                <span>{user.id}</span>
              </div>
            </div>
            <button className="ghost-button" onClick={handleLogout} type="button">
              退出
            </button>
          </div>
        </header>

        {renderTopFeedback()}

        {user.profile_status !== "completed" ? (
          <section className="content-card">
            <div className="card-title-row">
              <div>
                <p className="eyebrow">问诊准备</p>
                <h2>填写基本信息</h2>
              </div>
            </div>
            <form className="prep-form" onSubmit={handlePreparationSave}>
              <label>
                姓名
                <input name="full_name" defaultValue={String(profile.full_name || user.full_name || "")} />
              </label>
              <label>
                年龄
                <input name="age" defaultValue={String(profile.age || "")} />
              </label>
              <label>
                身高(cm)
                <input name="height_cm" defaultValue={String(profile.height_cm || "")} />
              </label>
              <label>
                体重(kg)
                <input name="weight_kg" defaultValue={String(profile.weight_kg || "")} />
              </label>
              <label>
                婚姻状况
                <input name="marital_status" defaultValue={String(profile.marital_status || "")} />
              </label>
              <label>
                父母婚姻状况
                <input name="parental_relationship" defaultValue={String(profile.parental_relationship || "")} />
              </label>
              <label>
                父母职业
                <input name="parental_occupation" defaultValue={String(profile.parental_occupation || "")} />
              </label>
              <label className="full-width">
                既往就诊史
                <textarea name="prior_psychiatric_visit" defaultValue={String(profile.prior_psychiatric_visit || "")} />
              </label>
              <label className="full-width">
                家族史
                <textarea name="family_history" defaultValue={String(profile.family_history || "")} />
              </label>
              <div className="form-actions full-width">
                <button className="primary-button" disabled={loading} type="submit">
                  保存问诊准备信息
                </button>
              </div>
            </form>
          </section>
        ) : assessment ? (
          <section className="assessment-page">
            <div className="assessment-main content-card">
              <div className="scale-stepper">
                {(assessment.selected_scales || []).map((slug, index) => {
                  const meta = assessmentCatalog.find((item) => item.slug === slug);
                  const isDone = (assessment.results || []).some((result) => result.scale_slug === slug);
                  const isCurrent = assessment.current_scale_slug === slug || (!assessment.current_scale_slug && isDone && index === (assessment.selected_scales || []).length - 1);
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

                {assessment.status === "completed" ? (
                  <div className="summary-code-block">
                    <pre>{JSON.stringify(assessment.aggregate_payload || {}, null, 2)}</pre>
                  </div>
                ) : (
                  <form className="assessment-form" onSubmit={handleSubmitAssessment}>
                    <div className="answer-grid">
                      {(assessment.current_item?.answer_options || []).map((option, index) => {
                        const tone = getAssessmentOptionTone(option.score, index);
                        return (
                          <button
                            key={`${assessment.current_item?.item_id}-${option.score}`}
                            className={`answer-card ${tone.className} ${selectedAssessmentScore === option.score ? "selected" : ""}`}
                            onClick={() => setSelectedAssessmentScore(option.score)}
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
                        onChange={(event) => setAssessmentRawInput(event.target.value)}
                        placeholder="后续接正式语音答案时，这里用于保存原始文本。"
                      />
                    </label>
                    <div className="bottom-action-row">
                      <button className="ghost-button disabled" disabled type="button">
                        上一题
                      </button>
                      <button className="ghost-button" onClick={() => void refreshAssessment()} type="button">
                        刷新状态
                      </button>
                      <div className="voice-hint">按住说话回答</div>
                      <button className="primary-button next-button" disabled={loading || selectedAssessmentScore === null} type="submit">
                        下一题
                      </button>
                    </div>
                  </form>
                )}
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
        ) : consultation ? (
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
                    <div className="doctor-caption">
                      {consultation.current_prompt || "您好，我将陪您完成本次心理问诊。"}
                    </div>
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
                      <button className="primary-button" disabled={loading} onClick={() => void handleStartAssessment()} type="button">
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
                            onChange={(event) => setConsultationInput(event.target.value)}
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
                <button className="ghost-button" onClick={() => void submitConsultationTurn({ input_type: "continue_button" })} type="button">
                  重说上一句
                </button>
                <button className="mic-button" disabled={loading} onClick={() => void submitManualConsultationTurn()} type="button">
                  按住说话
                </button>
                <button className="primary-button next-button" disabled={loading} onClick={() => void submitManualConsultationTurn()} type="button">
                  下一步
                </button>
              </div>

              <div className="assist-actions">
                <button className="text-button" onClick={() => void submitConsultationTurn({ input_type: "silence" })} type="button">
                  模拟沉默
                </button>
                <button className="text-button" onClick={() => void submitConsultationTurn({ input_type: "recognition_failure" })} type="button">
                  模拟识别失败
                </button>
                <button className="text-button" onClick={() => void refreshConsultation()} type="button">
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
                <p className="side-description">当前阶段：{getConsultationStageName()}</p>
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
        ) : (
          <section className="content-card readiness-page">
            <div className="card-title-row">
              <div>
                <p className="eyebrow">正式问诊入口</p>
                <h2>系统已自动绑定默认数字医生</h2>
              </div>
            </div>
            <p className="readiness-copy">
              当前患者资料已完善，下一步将创建规则版数字人问诊会话，并由系统自动切换到量表问诊阶段。
            </p>
            <div className="readiness-actions">
              <button className="primary-button" disabled={loading} onClick={() => void handleStartConsultation()} type="button">
                进入正式问诊
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
