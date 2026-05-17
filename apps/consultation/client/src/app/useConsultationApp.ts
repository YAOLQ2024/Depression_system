import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  clearSessionToken,
  getSessionPersistenceMode,
  getSessionPersistencePreference,
  hasSessionToken,
  setSessionPersistencePreference,
  setSessionToken,
} from "../services/api/client";
import type { AuthLoginPayload, AuthRegisterPayload } from "../features/auth/AuthPage";
import { resolveHomeEntryLabel, resolveHomeEntryPath, resolvePostLoginPath, resolveResumePath } from "../routes";
import { getAssessmentCatalog, getAssessmentSession, createAssessmentSession, submitAssessmentAnswer } from "../services/api/assessment.api";
import { login, logout, register } from "../services/api/auth.api";
import { getBootstrapSummary } from "../services/api/bootstrap.api";
import {
  completeConsultationQuestionItem,
  createConsultationSession,
  getConsultationSession,
  startConsultationSession,
  submitConsultationTurn as submitConsultationTurnRequest,
} from "../services/api/consultation.api";
import type { SubmitConsultationTurnPayload, UpdateUserProfilePayload } from "../services/api/contracts";
import { getCurrentUser, updateCurrentUserProfile } from "../services/api/user.api";
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

  const resumePath = useMemo(
    () =>
      resolveResumePath({
        user,
        consultation,
        assessment,
      }),
    [assessment, consultation, user],
  );

  const postLoginPath = useMemo(() => resolvePostLoginPath(user), [user]);

  const homeEntryPath = useMemo(
    () =>
      resolveHomeEntryPath({
        user,
        consultation,
        assessment,
      }),
    [assessment, consultation, user],
  );

  const homeEntryLabel = useMemo(
    () =>
      resolveHomeEntryLabel({
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
      return await getCurrentUser();
    } catch {
      clearSessionToken();
      return null;
    }
  }

  async function fetchBootstrap(): Promise<BootstrapPayload> {
    return getBootstrapSummary();
  }

  async function fetchAssessmentCatalog(): Promise<AssessmentCatalogItem[]> {
    return getAssessmentCatalog();
  }

  async function fetchExistingConsultation(currentUserId: string) {
    const sessionId = readConsultationSessionId(currentUserId);
    if (!sessionId) {
      return null;
    }

    try {
      return await getConsultationSession(sessionId);
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
      return await getAssessmentSession(sessionId);
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
      const loginData = await login({
        account: payload.account,
        password: payload.password,
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
      await register({
        full_name: payload.full_name,
        account: payload.account,
        password: payload.password,
      });
      setAuthMode("login");
      setMessage("注册成功，请使用新账号登录。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "注册失败");
    } finally {
      setLoading(false);
    }
  }

  async function savePreparationProfile(payload: UpdateUserProfilePayload) {
    resetFeedback();
    setLoading(true);

    try {
      const updatedUser = await updateCurrentUserProfile(payload);
      setUser(updatedUser);
      setConsultation(null);
      setAssessment(null);
      clearConsultationSessionId();
      clearAssessmentSessionId();
      setBootstrap(await fetchBootstrap());
      setAssessmentCatalog(await fetchAssessmentCatalog());
      setMessage("问诊准备信息已保存，可以进入正式问诊。");
      return updatedUser;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "资料保存失败");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function handleStartConsultation() {
    resetFeedback();
    setLoading(true);

    try {
      const created = await createConsultationSession();
      saveConsultationSessionId(created.session_id);

      const started = await startConsultationSession(created.session_id);

      setConsultation(started);
      setMessage("正式问诊已开始。");
      return started;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建问诊失败");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function submitConsultationTurn(payload: SubmitConsultationTurnPayload) {
    if (!consultation) {
      return;
    }

    resetFeedback();
    setLoading(true);

    try {
      const updatedConsultation = await submitConsultationTurnRequest(consultation.session_id, payload);

      setConsultation(updatedConsultation);
      if (updatedConsultation.status === "handoff_ready") {
        setMessage("规则问诊已完成，当前可以进入量表问诊。");
      } else if (updatedConsultation.status === "paused_for_human_review") {
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
      setConsultation(await getConsultationSession(consultation.session_id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "刷新失败");
    } finally {
      setLoading(false);
    }
  }

  async function completeConsultationSystemQuestionItem(questionKey: string) {
    if (!consultation) {
      return null;
    }

    resetFeedback();
    setLoading(true);

    try {
      const updatedConsultation = await completeConsultationQuestionItem(consultation.session_id, questionKey);
      setConsultation(updatedConsultation);
      if (updatedConsultation.status === "waiting_user_input") {
        setMessage("系统问候已播放完成，已进入当前题目的回答窗口。");
      } else if (updatedConsultation.status === "handoff_ready") {
        setMessage("数字人问诊已完成，可以进入量表评估。");
      } else {
        setMessage("系统问题项已自动推进。");
      }
      return updatedConsultation;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "系统问题项推进失败");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function handleStartAssessment() {
    if (!consultation) {
      return null;
    }

    resetFeedback();
    setLoading(true);

    try {
      const assessmentSession = await createAssessmentSession({
        consultation_session_id: consultation.session_id,
        scale_handoff_payload: consultation.scale_handoff_payload || {},
      });
      setAssessment(assessmentSession);
      saveAssessmentSessionId(assessmentSession.session_id);
      setMessage("量表问诊已开始。");
      return assessmentSession;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建量表会话失败");
      return null;
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
      const updatedAssessment = await submitAssessmentAnswer(assessment.session_id, {
        item_id: assessment.current_item?.item_id,
        selected_option_score: selectedAssessmentScore,
        raw_input: assessmentRawInput || null,
      });

      setAssessment(updatedAssessment);
      saveAssessmentSessionId(updatedAssessment.session_id);
      if (updatedAssessment.status === "completed") {
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
      setAssessment(await getAssessmentSession(assessment.session_id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "刷新量表失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    try {
      await logout();
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
      resumePath,
      postLoginPath,
      homeEntryPath,
      homeEntryLabel,
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
      savePreparationProfile,
      handleStartConsultation,
      submitConsultationTurn,
      submitManualConsultationTurn,
      refreshConsultation,
      completeConsultationSystemQuestionItem,
      handleStartAssessment,
      handleSubmitAssessment,
      refreshAssessment,
      handleLogout,
    },
  };
}

export type ConsultationAppStore = ReturnType<typeof useConsultationApp>;
