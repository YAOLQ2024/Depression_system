const API_BASE = window.__MCS_API_BASE__ || "http://127.0.0.1:8080/api/v1";

const state = {
  user: null,
  bootstrap: null,
  error: "",
  message: "",
};

const app = document.querySelector("#app");

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
    throw new Error(detail.message || payload.message || `Request failed (${response.status})`);
  }

  return payload.data || {};
}

function render(content) {
  app.innerHTML = `
    <div class="page-shell">
      <header class="topbar">
        <div>
          <p class="eyebrow">Multimodal Consultation System</p>
          <h1>Operations Console</h1>
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

function renderLogin() {
  render(`
    <section class="panel login-panel">
      <div>
        <h2>后台登录</h2>
        <p>Phase B 当前只允许 <code>admin</code> 和 <code>researcher</code> 进入后台。</p>
        <div class="hint-list">
          <p><strong>管理员：</strong> admin@mcs.local / Admin123!</p>
          <p><strong>研究员：</strong> researcher@mcs.local / Research123!</p>
        </div>
      </div>
      <form id="login-form" class="card compact">
        <label>邮箱<input name="email" type="email" value="admin@mcs.local" required /></label>
        <label>密码<input name="password" type="password" value="Admin123!" required /></label>
        <button type="submit">登录后台</button>
      </form>
    </section>
  `);

  app.querySelector("#login-form").addEventListener("submit", handleLogin);
}

function renderUnauthorized() {
  render(`
    <section class="panel">
      <h2>当前账号无后台权限</h2>
      <p>只有 <code>admin</code> 或 <code>researcher</code> 可访问 Operations Console。</p>
    </section>
  `);
}

function renderDashboard() {
  const workflow = state.bootstrap?.workflow || {};
  const personas = state.bootstrap?.doctor_personas || [];

  render(`
    <section class="dashboard-grid">
      <article class="panel metric">
        <p class="eyebrow">Workflow</p>
        <h2>${workflow.title || "consultation-v1"}</h2>
        <p>阶段数：${workflow.stage_count || 0}</p>
      </article>
      <article class="panel metric">
        <p class="eyebrow">Doctor Personas</p>
        <h2>${personas.length}</h2>
        <p>系统当前可装载的数字医生人设配置目录</p>
      </article>
      <article class="panel metric">
        <p class="eyebrow">Current Operator</p>
        <h2>${state.user.full_name}</h2>
        <p>${state.user.email}</p>
      </article>
    </section>
    <section class="panel">
      <h3>流程阶段</h3>
      <div class="stage-list">
        ${(workflow.stages || [])
          .map(
            (stage) => `
            <div class="stage-item">
              <strong>${stage.name}</strong>
              <span>${stage.id}</span>
              <small>${stage.type}</small>
            </div>
          `
          )
          .join("")}
      </div>
    </section>
    <section class="panel">
      <h3>数字人配置目录</h3>
      <div class="persona-list">
        ${personas
          .map(
            (persona) => `
            <div class="persona-item">
              <strong>${persona.display_name}</strong>
              <span>${persona.voice_style}</span>
              <small>${persona.tone_style}</small>
            </div>
          `
          )
          .join("")}
      </div>
    </section>
  `);
}

async function handleLogin(event) {
  event.preventDefault();
  state.error = "";
  state.message = "";
  const formData = new FormData(event.currentTarget);
  try {
    await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: formData.get("email"),
        password: formData.get("password"),
      }),
    });
    await initAuthenticatedState();
    state.message = "后台登录成功。";
  } catch (error) {
    state.error = error.message;
  }
  renderCurrent();
}

async function handleLogout() {
  try {
    await apiRequest("/auth/logout", { method: "POST" });
  } catch (error) {
    // ignore
  }
  state.user = null;
  state.bootstrap = null;
  state.message = "已退出。";
  state.error = "";
  renderCurrent();
}

async function initAuthenticatedState() {
  try {
    const me = await apiRequest("/users/me", { method: "GET" });
    state.user = me.user;
    state.bootstrap = await apiRequest("/system/bootstrap", { method: "GET" });
  } catch (error) {
    state.user = null;
    state.bootstrap = null;
  }
}

function renderCurrent() {
  if (!state.user) {
    renderLogin();
    return;
  }
  if (!["admin", "researcher"].includes(state.user.role)) {
    renderUnauthorized();
    return;
  }
  renderDashboard();
}

initAuthenticatedState().then(renderCurrent);
