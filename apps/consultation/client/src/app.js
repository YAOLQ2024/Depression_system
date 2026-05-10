const API_BASE = window.__MCS_API_BASE__ || "http://127.0.0.1:8080/api/v1";

const STAGE_LABELS = {
  "stage-01-greeting-and-briefing": "初始问候与流程说明",
  "stage-02-chief-complaint": "主诉采集",
  "stage-03-current-history-followup": "现病史规则式问诊",
  "stage-04-high-risk-screening": "高风险问题排查",
  "handoff-to-scale-assessment": "量表移交",
};

const state = {
  user: null,
  bootstrap: null,
  consultation: null,
  assessment: null,
  assessmentCatalog: [],
  message: "",
  error: "",
  loading: false,
};

const app = document.querySelector("#app");

function setMessage(message = "") {
  state.message = message;
}

function setError(message = "") {
  state.error = message;
}

function setLoading(isLoading) {
  state.loading = Boolean(isLoading);
}

function getSessionStorageKey() {
  return state.user ? `mcs_consultation_session:${state.user.id}` : null;
}

function saveSessionId(sessionId) {
  const key = getSessionStorageKey();
  if (!key || !sessionId) {
    return;
  }
  window.localStorage.setItem(key, sessionId);
}

function readSessionId() {
  const key = getSessionStorageKey();
  if (!key) {
    return null;
  }
  return window.localStorage.getItem(key);
}

function clearSessionId() {
  const key = getSessionStorageKey();
  if (!key) {
    return;
  }
  window.localStorage.removeItem(key);
}

function getAssessmentStorageKey() {
  return state.user ? `mcs_assessment_session:${state.user.id}` : null;
}

function saveAssessmentSessionId(sessionId) {
  const key = getAssessmentStorageKey();
  if (!key || !sessionId) {
    return;
  }
  window.localStorage.setItem(key, sessionId);
}

function readAssessmentSessionId() {
  const key = getAssessmentStorageKey();
  if (!key) {
    return null;
  }
  return window.localStorage.getItem(key);
}

function clearAssessmentSessionId() {
  const key = getAssessmentStorageKey();
  if (!key) {
    return;
  }
  window.localStorage.removeItem(key);
}

function findPersonaName(personaId) {
  const items = state.bootstrap?.doctor_personas || [];
  const match = items.find((item) => item.persona_id === personaId);
  return match?.display_name || personaId || "默认数字医生";
}

function getCurrentStageLabel() {
  const consultation = state.consultation;
  if (!consultation?.current_stage_id) {
    return "等待下一阶段";
  }
  return STAGE_LABELS[consultation.current_stage_id] || consultation.current_stage_id;
}

function consultationIsTerminal() {
  return ["handoff_ready", "paused_for_human_review"].includes(state.consultation?.status);
}

function assessmentIsCompleted() {
  return state.assessment?.status === "completed";
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let payload = {};
  try {
    payload = await response.json();
  } catch (error) {
    payload = {};
  }

  if (!response.ok || payload.code !== 0) {
    const detail = payload.detail || payload;
    const message = detail.message || payload.message || `Request failed (${response.status})`;
    throw new Error(message);
  }

  return payload.data || {};
}

async function loadUser() {
  try {
    const data = await apiRequest("/users/me", { method: "GET" });
    state.user = data.user;
  } catch (error) {
    state.user = null;
  }
}

async function loadBootstrap() {
  state.bootstrap = await apiRequest("/system/bootstrap", { method: "GET" });
}

async function loadAssessmentCatalog() {
  const data = await apiRequest("/assessment/catalog", { method: "GET" });
  state.assessmentCatalog = data.catalog || [];
}

async function loadExistingConsultation() {
  state.consultation = null;
  const sessionId = readSessionId();
  if (!sessionId) {
    return;
  }
  try {
    const data = await apiRequest(`/consultations/${sessionId}`, { method: "GET" });
    state.consultation = data.consultation;
  } catch (error) {
    clearSessionId();
    state.consultation = null;
  }
}

async function loadExistingAssessment() {
  state.assessment = null;
  const sessionId = readAssessmentSessionId();
  if (!sessionId) {
    return;
  }
  try {
    const data = await apiRequest(`/assessment/sessions/${sessionId}`, { method: "GET" });
    state.assessment = data.assessment_session;
  } catch (error) {
    clearAssessmentSessionId();
    state.assessment = null;
  }
}

async function refreshConsultation() {
  const sessionId = state.consultation?.session_id || readSessionId();
  if (!sessionId) {
    return;
  }
  const data = await apiRequest(`/consultations/${sessionId}`, { method: "GET" });
  state.consultation = data.consultation;
  saveSessionId(data.consultation.session_id);
}

async function refreshAssessment() {
  const sessionId = state.assessment?.session_id || readAssessmentSessionId();
  if (!sessionId) {
    return;
  }
  const data = await apiRequest(`/assessment/sessions/${sessionId}`, { method: "GET" });
  state.assessment = data.assessment_session;
  saveAssessmentSessionId(data.assessment_session.session_id);
}

function renderShell(content) {
  app.innerHTML = `
    <div class="page-shell">
      <header class="topbar">
        <div>
          <p class="eyebrow">Multimodal Consultation System</p>
          <h1>Consultation</h1>
        </div>
        ${
          state.user
            ? `
          <div class="topbar-actions">
            <div class="identity-chip">
              <span>${state.user.full_name}</span>
              <small>${state.user.role}</small>
            </div>
            <button class="ghost-button" data-action="logout">退出</button>
          </div>
        `
            : ""
        }
      </header>
      ${state.message ? `<div class="banner success">${state.message}</div>` : ""}
      ${state.error ? `<div class="banner error">${state.error}</div>` : ""}
      ${content}
    </div>
  `;

  const logoutButton = app.querySelector('[data-action="logout"]');
  if (logoutButton) {
    logoutButton.addEventListener("click", handleLogout);
  }
}

function renderAuthScreen() {
  renderShell(`
    <section class="panel auth-grid">
      <div class="auth-info">
        <h2>患者主链入口</h2>
        <p>当前已接通：登录、问诊准备、规则版数字人问诊、量表移交状态。</p>
        <div class="credential-list">
          <div>
            <strong>受试者示例账号</strong>
            <p>participant@mcs.local / Participant123!</p>
          </div>
          <div>
            <strong>管理员示例账号</strong>
            <p>admin@mcs.local / Admin123!</p>
          </div>
        </div>
      </div>
      <div class="auth-forms">
        <form id="login-form" class="card">
          <h3>登录</h3>
          <label>邮箱<input name="email" type="email" value="participant@mcs.local" required /></label>
          <label>密码<input name="password" type="password" value="Participant123!" required /></label>
          <button type="submit">登录</button>
        </form>
        <form id="register-form" class="card">
          <h3>注册新受试者</h3>
          <label>姓名<input name="full_name" type="text" required /></label>
          <label>邮箱<input name="email" type="email" required /></label>
          <label>密码<input name="password" type="password" minlength="8" required /></label>
          <button type="submit">注册</button>
        </form>
      </div>
    </section>
  `);

  app.querySelector("#login-form").addEventListener("submit", handleLogin);
  app.querySelector("#register-form").addEventListener("submit", handleRegister);
}

function renderPreparationScreen() {
  const profile = state.user.profile || {};
  renderShell(`
    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Step 1</p>
          <h2>问诊准备：基础资料确认</h2>
        </div>
        <span class="status-pill">profile_status: ${state.user.profile_status}</span>
      </div>
      <div class="workflow-summary">
        <p>先确认基础资料和开始问诊前的准备状态，正式规则问诊将在下一步由系统自动绑定默认数字医生并启动。</p>
        <small>这里仍然只保存问诊准备字段，不承载现病史追问和高风险排查本体。</small>
      </div>
      <form id="profile-form" class="profile-grid">
        <label>姓名<input name="full_name" type="text" value="${state.user.full_name || ""}" required /></label>
        <label>年龄<input name="age" type="number" min="0" max="120" value="${profile.age ?? ""}" /></label>
        <label>身高(cm)<input name="height_cm" type="number" min="0" step="0.1" value="${profile.height_cm ?? ""}" /></label>
        <label>体重(kg)<input name="weight_kg" type="number" min="0" step="0.1" value="${profile.weight_kg ?? ""}" /></label>
        <label>婚姻状况<input name="marital_status" type="text" value="${profile.marital_status ?? ""}" /></label>
        <label>父母婚姻状况<input name="parents_marital_status" type="text" value="${profile.parents_marital_status ?? ""}" /></label>
        <label>父母职业<input name="parents_occupation" type="text" value="${profile.parents_occupation ?? ""}" /></label>
        <label>既往就诊史<textarea name="prior_psychiatric_visit">${profile.prior_psychiatric_visit ?? ""}</textarea></label>
        <label>家族史<textarea name="family_history">${profile.family_history ?? ""}</textarea></label>
        <div class="form-actions">
          <button type="submit"${state.loading ? " disabled" : ""}>保存问诊准备信息</button>
        </div>
      </form>
    </section>
  `);

  app.querySelector("#profile-form").addEventListener("submit", handlePreparationSave);
}

function renderReadinessScreen() {
  const workflow = state.bootstrap?.workflow;
  const nextStages = (workflow?.stages || []).slice(2, 5);

  renderShell(`
    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Step 2</p>
          <h2>正式问诊入口</h2>
        </div>
        <span class="status-pill">workflow: ${workflow?.workflow_id || "consultation-v1"}</span>
      </div>
      <div class="workflow-summary">
        <p>${workflow?.title || "Consultation Workflow"}</p>
        <small>系统将自动绑定默认数字医生，不再让患者前台选择数字医生样式。</small>
      </div>
      <div class="consultation-layout">
        <div class="card">
          <h3>当前状态</h3>
          <p>问诊准备资料已经保存完成。下一步将创建规则版问诊会话，并由 <code>consultation-service</code> 驱动 4 个固定子模块。</p>
          <div class="session-meta">
            <span class="stage-pill">默认数字医生：${findPersonaName("doctor-a-calm-female")}</span>
            <span class="stage-pill">后端引擎：rule-v1</span>
          </div>
          <div class="form-actions">
            <button id="start-consultation-button"${state.loading ? " disabled" : ""}>进入正式问诊</button>
          </div>
        </div>
        <div class="card">
          <h3>后续主链</h3>
          <div class="credential-list">
            ${nextStages
              .map(
                (stage) => `
                <div>
                  <strong>${stage.name}</strong>
                  <p>${stage.id}</p>
                </div>
              `,
              )
              .join("")}
          </div>
        </div>
      </div>
    </section>
  `);

  app.querySelector("#start-consultation-button").addEventListener("click", handleStartConsultation);
}

function renderAssessmentScreen() {
  const assessment = state.assessment;
  const currentItem = assessment.current_item;
  const completed = assessmentIsCompleted();
  const currentScale = state.assessmentCatalog.find((item) => item.slug === assessment.current_scale_slug);
  const progressTotal = assessment.selected_scales?.length || 0;
  const progressDone = assessment.results?.length || 0;

  renderShell(`
    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">量表问诊</p>
          <h2>${completed ? "量表阶段已完成" : currentScale?.name || assessment.current_scale_slug || "量表进行中"}</h2>
        </div>
        <div class="session-meta">
          <span class="stage-pill">状态：${assessment.status}</span>
          <span class="stage-pill">已完成量表：${progressDone}/${progressTotal}</span>
        </div>
      </div>
      <div class="consultation-layout">
        <div class="card consultation-card">
          ${
            completed
              ? `
            <div class="alert-card success-card">
              <h3>量表阶段已完成</h3>
              <p>四个活跃量表已完成，聚合结果已经生成，下一步可以进入临床决策阶段。</p>
            </div>
            <div class="prompt-card">
              <p class="eyebrow">聚合结果</p>
              <pre>${JSON.stringify(assessment.aggregate_payload || {}, null, 2)}</pre>
            </div>
          `
              : `
            <div class="prompt-card">
              <p class="eyebrow">当前题目</p>
              <p>${currentItem?.index || assessment.current_item_index + 1}. ${currentItem?.text || "系统正在准备题目。"}</p>
            </div>
            <form id="assessment-form" class="card composer-card">
              <div class="option-grid">
                ${(currentItem?.answer_options || [])
                  .map(
                    (option) => `
                    <label class="option-card">
                      <input type="radio" name="assessment_score" value="${option.score}" />
                      <span>${option.label}</span>
                      <small>分值 ${option.score}</small>
                    </label>
                  `,
                  )
                  .join("")}
              </div>
              <label>语音/文本原始输入兜底
                <textarea id="assessment-raw-input" name="assessment_raw_input" placeholder="可选。后续接正式语音答案时，这里会记录原始文本。"></textarea>
              </label>
              <div class="composer-actions">
                <button type="submit"${state.loading ? " disabled" : ""}>提交本题答案</button>
                <button type="button" class="ghost-button" data-assessment-action="refresh"${state.loading ? " disabled" : ""}>刷新量表状态</button>
              </div>
            </form>
          `
          }
        </div>
        <div class="card">
          <h3>量表摘要</h3>
          <div class="summary-grid">
            <div>
              <strong>量表顺序</strong>
              <p>${(assessment.selected_scales || []).join(" -> ")}</p>
            </div>
            <div>
              <strong>当前量表结果</strong>
              <pre>${JSON.stringify(assessment.results || [], null, 2)}</pre>
            </div>
            <div>
              <strong>问诊移交数据</strong>
              <pre>${JSON.stringify(assessment.scale_handoff_payload || {}, null, 2)}</pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  `);

  if (!completed) {
    app.querySelector("#assessment-form").addEventListener("submit", handleAssessmentAnswerSubmit);
    app.querySelectorAll("[data-assessment-action]").forEach((button) => {
      button.addEventListener("click", handleAssessmentAction);
    });
  }
}

function renderConsultationScreen() {
  const consultation = state.consultation;
  const prompt = consultation.current_prompt || "系统正在准备下一节点。";
  const stageLabel = getCurrentStageLabel();
  const personaName = findPersonaName(consultation.assigned_doctor_persona);
  const handoffReady = consultation.status === "handoff_ready";
  const humanReview = consultation.status === "paused_for_human_review";

  renderShell(`
    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">数字人交互问诊</p>
          <h2>${stageLabel}</h2>
        </div>
        <div class="session-meta">
          <span class="stage-pill">状态：${consultation.status}</span>
          <span class="stage-pill">数字医生：${personaName}</span>
        </div>
      </div>
      <div class="consultation-layout">
        <div class="card consultation-card">
          <div class="prompt-card">
            <p class="eyebrow">当前提示</p>
            <p>${prompt}</p>
          </div>
          ${
            humanReview
              ? `
            <div class="alert-card">
              <h3>人工复核已触发</h3>
              <p>系统检测到当前会话存在高风险信号，标准问诊主链已暂停，后续应交由人工支持处理。</p>
            </div>
          `
              : ""
          }
          ${
            handoffReady
              ? `
            <div class="alert-card success-card">
              <h3>已完成规则问诊</h3>
              <p>问诊主链已完成，当前可以进入量表问诊阶段。</p>
              <div class="form-actions">
                <button id="start-assessment-button"${state.loading ? " disabled" : ""}>进入量表问诊</button>
              </div>
            </div>
          `
              : `
            <form id="turn-form" class="card composer-card">
              <label>文字输入兜底
                <textarea id="turn-text" name="turn_text" placeholder="如果不方便模拟语音，可以直接在这里输入患者回答。"></textarea>
              </label>
              <div class="composer-actions">
                <button type="submit"${state.loading ? " disabled" : ""}>提交文字回答</button>
                <button type="button" class="ghost-button" data-turn-action="continue"${state.loading ? " disabled" : ""}>继续</button>
                <button type="button" class="ghost-button" data-turn-action="silence"${state.loading ? " disabled" : ""}>模拟沉默</button>
                <button type="button" class="ghost-button" data-turn-action="recognition_failure"${state.loading ? " disabled" : ""}>模拟识别失败</button>
                <button type="button" class="ghost-button" data-turn-action="refresh"${state.loading ? " disabled" : ""}>刷新状态</button>
              </div>
              <p class="muted">当前前端先以文字输入模拟语音结果，后续再接正式 ASR / 数字人通道。</p>
            </form>
          `
          }
        </div>
        <div class="card">
          <h3>结构化摘要</h3>
          <div class="summary-grid">
            <div>
              <strong>主诉摘要</strong>
              <p>${consultation.chief_complaint_summary || "暂未形成"}</p>
            </div>
            <div>
              <strong>现病史结果</strong>
              <pre>${JSON.stringify(consultation.current_history_structured_result || {}, null, 2)}</pre>
            </div>
            <div>
              <strong>高风险结果</strong>
              <pre>${JSON.stringify(consultation.high_risk_screening_result || {}, null, 2)}</pre>
            </div>
            <div>
              <strong>量表移交</strong>
              <pre>${JSON.stringify(consultation.scale_handoff_payload || {}, null, 2)}</pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  `);

  if (!handoffReady && !humanReview) {
    app.querySelector("#turn-form").addEventListener("submit", handleManualTurnSubmit);
    app.querySelectorAll("[data-turn-action]").forEach((button) => {
      button.addEventListener("click", handleTurnAction);
    });
  }
  if (handoffReady) {
    app.querySelector("#start-assessment-button").addEventListener("click", handleStartAssessment);
  }
}

async function handleLogin(event) {
  event.preventDefault();
  setMessage("");
  setError("");
  const formData = new FormData(event.currentTarget);
  try {
    await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: formData.get("email"),
        password: formData.get("password"),
      }),
    });
    await bootstrapAuthenticatedState();
    setMessage("登录成功。");
  } catch (error) {
    setError(error.message);
  }
  render();
}

async function handleRegister(event) {
  event.preventDefault();
  setMessage("");
  setError("");
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
    setMessage("注册成功，请使用新账号登录。");
  } catch (error) {
    setError(error.message);
  }
  render();
}

async function handlePreparationSave(event) {
  event.preventDefault();
  setMessage("");
  setError("");
  setLoading(true);
  const formData = new FormData(event.currentTarget);
  const payload = Object.fromEntries(formData.entries());
  ["age", "height_cm", "weight_kg"].forEach((field) => {
    if (payload[field] === "") {
      delete payload[field];
      return;
    }
    payload[field] = Number(payload[field]);
  });
  try {
    const data = await apiRequest("/users/me/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    state.user = data.user;
    state.consultation = null;
    state.assessment = null;
    clearSessionId();
    clearAssessmentSessionId();
    await loadBootstrap();
    setMessage("问诊准备信息已保存，可以进入正式问诊。");
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(false);
  }
  render();
}

async function handleStartConsultation() {
  setMessage("");
  setError("");
  setLoading(true);
  try {
    const created = await apiRequest("/consultations", {
      method: "POST",
      body: JSON.stringify({}),
    });
    const sessionId = created.consultation.session_id;
    saveSessionId(sessionId);
    const started = await apiRequest(`/consultations/${sessionId}/start`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    state.consultation = started.consultation;
    setMessage("正式问诊已开始。");
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(false);
  }
  render();
}

async function handleStartAssessment() {
  setMessage("");
  setError("");
  setLoading(true);
  try {
    if (!state.assessmentCatalog.length) {
      await loadAssessmentCatalog();
    }
    const created = await apiRequest("/assessment/sessions", {
      method: "POST",
      body: JSON.stringify({
        consultation_session_id: state.consultation.session_id,
        scale_handoff_payload: state.consultation.scale_handoff_payload || {},
      }),
    });
    state.assessment = created.assessment_session;
    saveAssessmentSessionId(state.assessment.session_id);
    setMessage("量表问诊已开始。");
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(false);
  }
  render();
}

async function handleManualTurnSubmit(event) {
  event.preventDefault();
  const textValue = app.querySelector("#turn-text")?.value?.trim() || "";
  if (!textValue) {
    setError("请先输入本轮患者回答。");
    render();
    return;
  }
  await submitTurn({
    input_type: "manual_input",
    raw_input: textValue,
    transcript_text: textValue,
  });
}

async function handleTurnAction(event) {
  const action = event.currentTarget.dataset.turnAction;
  if (action === "refresh") {
    setMessage("");
    setError("");
    setLoading(true);
    try {
      await refreshConsultation();
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
    render();
    return;
  }

  if (action === "continue") {
    await submitTurn({ input_type: "continue_button" });
    return;
  }

  if (action === "silence") {
    await submitTurn({ input_type: "silence" });
    return;
  }

  if (action === "recognition_failure") {
    await submitTurn({ input_type: "recognition_failure" });
  }
}

async function submitTurn(payload) {
  setMessage("");
  setError("");
  setLoading(true);
  try {
    const data = await apiRequest(`/consultations/${state.consultation.session_id}/turns`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.consultation = data.consultation;
    if (state.consultation.status === "handoff_ready") {
      setMessage("规则问诊已完成，当前已到达量表移交状态。");
    } else if (state.consultation.status === "paused_for_human_review") {
      setError("系统已触发高风险人工复核，标准问诊主链已暂停。");
    } else {
      setMessage("本轮输入已提交。");
    }
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(false);
  }
  render();
}

async function handleAssessmentAnswerSubmit(event) {
  event.preventDefault();
  const checked = app.querySelector('input[name="assessment_score"]:checked');
  if (!checked) {
    setError("请先选择本题答案。");
    render();
    return;
  }
  setMessage("");
  setError("");
  setLoading(true);
  try {
    const data = await apiRequest(`/assessment/sessions/${state.assessment.session_id}/answers`, {
      method: "POST",
      body: JSON.stringify({
        item_id: state.assessment.current_item?.item_id,
        selected_option_score: Number(checked.value),
        raw_input: app.querySelector("#assessment-raw-input")?.value?.trim() || null,
      }),
    });
    state.assessment = data.assessment_session;
    saveAssessmentSessionId(state.assessment.session_id);
    if (state.assessment.status === "completed") {
      setMessage("量表问诊已完成，已生成聚合结果。");
    } else {
      setMessage("量表答案已提交。");
    }
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(false);
  }
  render();
}

async function handleAssessmentAction(event) {
  const action = event.currentTarget.dataset.assessmentAction;
  if (action !== "refresh") {
    return;
  }
  setMessage("");
  setError("");
  setLoading(true);
  try {
    await refreshAssessment();
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(false);
  }
  render();
}

async function handleLogout() {
  try {
    await apiRequest("/auth/logout", { method: "POST" });
  } catch (error) {
    // ignore logout API failure and still clear local state
  }
  clearSessionId();
  clearAssessmentSessionId();
  state.user = null;
  state.bootstrap = null;
  state.consultation = null;
  state.assessment = null;
  setMessage("已退出。");
  setError("");
  render();
}

async function bootstrapAuthenticatedState() {
  await loadUser();
  if (!state.user) {
    state.bootstrap = null;
    state.consultation = null;
    return;
  }
  await loadBootstrap();
  await loadAssessmentCatalog();
  if (state.user.profile_status === "completed") {
    await loadExistingConsultation();
    if (state.consultation?.status === "handoff_ready") {
      await loadExistingAssessment();
    } else {
      state.assessment = null;
      clearAssessmentSessionId();
    }
  } else {
    state.consultation = null;
    state.assessment = null;
    clearSessionId();
    clearAssessmentSessionId();
  }
}

function render() {
  if (!state.user) {
    renderAuthScreen();
    return;
  }
  if (state.user.profile_status !== "completed") {
    renderPreparationScreen();
    return;
  }
  if (state.consultation) {
    if (state.assessment) {
      renderAssessmentScreen();
      return;
    }
    renderConsultationScreen();
    return;
  }
  renderReadinessScreen();
}

async function init() {
  setMessage("");
  setError("");
  try {
    await bootstrapAuthenticatedState();
  } catch (error) {
    setError(error.message);
  }
  render();
}

init();
