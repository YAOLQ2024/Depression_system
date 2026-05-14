import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  apiRequest,
  clearSessionToken,
  getSessionPersistenceMode,
  getSessionPersistencePreference,
  hasSessionToken,
  setSessionPersistencePreference,
  setSessionToken,
} from "../api";
import type { AuthLoginPayload, AuthRegisterPayload } from "../features/auth/AuthPage";
import { resolveAppPath } from "../routes";
import type {
  AssessmentCatalogItem,
  AssessmentSession,
  BootstrapPayload,
  ConsultationSession,
  UserRecord,
} from "../types";

export function useConsultationApp() {
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
  const [keepLoggedIn, setKeepLoggedIn] = useState(() => getSessionPersistencePreference());
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

  const resolvedPath = useMemo(
    () =>
      resolveAppPath({
        user,
        consultation,
        assessment,
      }),
    [assessment, consultation, user],
  );

  const currentScaleMeta = assessmentCatalog.find((item) => item.slug === assessment?.current_scale_slug) || null;

  function getSessionStorageKey(userId?: string | null) {
    return userId ? `mcs_consultation_session:${userId}` : null;
  }

  function getAssessmentStorageKey(userId?: string | null) {
    return userId ? `mcs_assessment_session:${userId}` : null;
  }

  function writeScopedStorageValue(key: string, value: string, persist = keepLoggedIn) {
    const primaryStorage = persist ? window.localStorage : window.sessionStorage;
    const secondaryStorage = persist ? window.sessionStorage : window.localStorage;
    secondaryStorage.removeItem(key);
    primaryStorage.setItem(key, value);
  }

  function readScopedStorageValue(key: string) {
    const primaryStorage = getSessionPersistenceMode() === "session" ? window.sessionStorage : window.localStorage;
    const secondaryStorage = primaryStorage === window.localStorage ? window.sessionStorage : window.localStorage;
    return primaryStorage.getItem(key) ?? secondaryStorage.getItem(key);
  }

  function clearScopedStorageValue(key: string) {
    window.localStorage.removeItem(key);
    window.sessionStorage.removeItem(key);
  }

  function saveConsultationSessionId(sessionId: string, userId?: string | null) {
    const key = getSessionStorageKey(userId || user?.id);
    if (key) {
      writeScopedStorageValue(key, sessionId);
    }
  }

  function readConsultationSessionId(userId?: string | null) {
    const key = getSessionStorageKey(userId || user?.id);
    return key ? readScopedStorageValue(key) : null;
  }

  function clearConsultationSessionId(userId?: string | null) {
    const key = getSessionStorageKey(userId || user?.id);
    if (key) {
      clearScopedStorageValue(key);
    }
  }

  function saveAssessmentSessionId(sessionId: string, userId?: string | null) {
    const key = getAssessmentStorageKey(userId || user?.id);
    if (key) {
      writeScopedStorageValue(key, sessionId);
    }
  }

  function readAssessmentSessionId(userId?: string | null) {
    const key = getAssessmentStorageKey(userId || user?.id);
    return key ? readScopedStorageValue(key) : null;
  }

  function clearAssessmentSessionId(userId?: string | null) {
    const key = getAssessmentStorageKey(userId || user?.id);
    if (key) {
      clearScopedStorageValue(key);
    }
  }

  function resetFeedback() {
    setMessage("");
    setError("");
  }

  async function fetchCurrentUser(): Promise<UserRecord | null> {
    if (!hasSessionToken()) {
      return null;
    }

    try {
      const data = await apiRequest<{ user: UserRecord }>("/users/me", { method: "GET" });
      return data.user;
    } catch {
      clearSessionToken();
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

  function handleKeepLoggedInChange(checked: boolean) {
    setKeepLoggedIn(checked);
    setSessionPersistencePreference(checked);
  }

  async function handleLogin(payload: AuthLoginPayload) {
    resetFeedback();
    setLoading(true);

    try {
      const loginData = await apiRequest<{ user: UserRecord; session_token?: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          account: payload.account,
          password: payload.password,
        }),
      });

      if (loginData.session_token) {
        setSessionToken(loginData.session_token, { persist: keepLoggedIn });
      }

      await new Promise((resolve) => window.setTimeout(resolve, 120));
      await hydrateAuthenticatedState(loginData.user);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(payload: AuthRegisterPayload) {
    resetFeedback();
    setLoading(true);

    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: payload.full_name,
          account: payload.account,
          password: payload.password,
        }),
      });
      setAuthMode("login");
      setMessage("注册成功，请使用新账号登录。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "注册失败");
    } finally {
      setLoading(false);
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
    setMessage("");
    setError("");
  }

  return {
    state: {
      user,
      bootstrap,
      consultation,
      assessment,
      assessmentCatalog,
      currentScaleMeta,
      message,
      error,
      loading,
      authMode,
      passwordVisible,
      keepLoggedIn,
      consultationInput,
      assessmentRawInput,
      selectedAssessmentScore,
      resolvedPath,
    },
    actions: {
      setAuthMode,
      setPasswordVisible,
      setConsultationInput,
      setAssessmentRawInput,
      setSelectedAssessmentScore,
      resetFeedback,
      handleKeepLoggedInChange,
      handleLogin,
      handleRegister,
      handlePreparationSave,
      handleStartConsultation,
      submitConsultationTurn,
      submitManualConsultationTurn,
      refreshConsultation,
      handleStartAssessment,
      handleSubmitAssessment,
      refreshAssessment,
      handleLogout,
    },
  };
}
