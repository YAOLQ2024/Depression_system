import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  clearSessionToken,
  getSessionPersistenceMode,
  getSessionPersistencePreference,
  hasSessionToken,
  setSessionPersistencePreference,
  setSessionToken,
  ApiRequestError,
} from "../services/api/client";
import type { AuthLoginPayload, AuthRegisterPayload } from "../features/auth/AuthPage";
import { resolveHomeEntryLabel, resolveHomeEntryPath, resolvePostLoginPath, resolveResumePath } from "../routes";
import {
  getAssessmentCatalog,
  getAssessmentMultimodalLive,
  getAssessmentSession,
  createAssessmentSession,
  submitAssessmentAnswer,
} from "../services/api/assessment.api";
import { login, logout, register } from "../services/api/auth.api";
import { getBootstrapSummary } from "../services/api/bootstrap.api";
import {
  completeConsultationQuestionItem,
  createConsultationSession,
  getConsultationMultimodalLive,
  getConsultationSession,
  getConsultationTurnMultimodalBundle,
  previewConsultationQuestionItemCompletion,
  startConsultationSession,
  submitConsultationVisualCapture as submitConsultationVisualCaptureRequest,
  submitConsultationTurn as submitConsultationTurnRequest,
} from "../services/api/consultation.api";
import type {
  AssessmentAcceptedAnswer,
  CreateConsultationSessionPayload,
  ConsultationMultimodalCapturePayload,
  ConsultationFrameCaptureResponse,
  ConsultationVisualCaptureResponse,
  SubmitConsultationTurnPayload,
  SubmitAssessmentAnswerPayload,
  UpdateUserPreparationStatePayload,
  UpdateUserProfilePayload,
} from "../services/api/contracts";
import {
  getCurrentUser,
  updateCurrentUserPreparationState,
  updateCurrentUserProfile,
} from "../services/api/user.api";
import type {
  AssessmentCatalogItem,
  AssessmentSession,
  BootstrapPayload,
  ConsultationMultimodalLive,
  ConsultationMultimodalLivePatch,
  ConsultationSession,
  UserRecord,
} from "../types";
import { mergeConsultationMultimodalLive } from "../lib/multimodalLiveMerge";

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

  function mergeConsultationWithCurrentTurnBundle(nextConsultation: ConsultationSession) {
    const currentBundle = consultation?.current_turn_bundle || null;
    const currentVisualPipeline = consultation?.visual_pipeline || null;
    if (
      currentBundle &&
      currentBundle.turn_id &&
      nextConsultation.current_turn_id &&
      currentBundle.turn_id === nextConsultation.current_turn_id
    ) {
      return {
        ...nextConsultation,
        current_turn_bundle: currentBundle,
        visual_pipeline: currentVisualPipeline,
      };
    }
    return {
      ...nextConsultation,
      current_turn_bundle: null,
      visual_pipeline: currentVisualPipeline,
    };
  }

  function isMissingConsultationTurnBundleError(error: unknown) {
    if (!(error instanceof Error)) {
      return false;
    }

    const message = error.message.toLowerCase();
    return (
      message.includes("consultation turn not found") ||
      message.includes("multimodal turn bundle not found")
    );
  }

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

  function clearPersistedFlowState() {
    for (const storage of [window.localStorage, window.sessionStorage]) {
      for (const key of Object.keys(storage)) {
        if (
          key.startsWith("mcs_consultation_session:") ||
          key.startsWith("mcs_assessment_session:")
        ) {
          storage.removeItem(key);
        }
      }
    }
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
      clearPersistedFlowState();
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
      setConsultation(existingConsultation ? mergeConsultationWithCurrentTurnBundle(existingConsultation) : existingConsultation);

      if (existingConsultation?.status === "handoff_ready" || !existingConsultation) {
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

  async function savePreparationState(payload: UpdateUserPreparationStatePayload) {
    const updatedUser = await updateCurrentUserPreparationState(payload);
    if (updatedUser) {
      setUser(updatedUser);
    }
    return updatedUser;
  }

  async function handleStartConsultation(payload: CreateConsultationSessionPayload = {}) {
    resetFeedback();
    setLoading(true);

    try {
      clearAssessmentSessionId();
      setAssessment(null);
      const created = await createConsultationSession(payload);
      saveConsultationSessionId(created.session_id);

      const started = await startConsultationSession(created.session_id);

      setConsultation(mergeConsultationWithCurrentTurnBundle(started));
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

      setConsultation(mergeConsultationWithCurrentTurnBundle(updatedConsultation));
      if (updatedConsultation.status === "handoff_ready") {
        setMessage("可以进入量表评估");
      } else if (updatedConsultation.status === "paused_for_human_review") {
        setError("系统已触发高风险人工复核，标准问诊主链已暂停。");
      } else {
        setMessage("");
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
      turn_id: consultation?.current_turn_id || null,
      raw_input: normalized,
      transcript_text: normalized,
      transcript_source: "manual_input",
    });
  }

  async function refreshConsultation() {
    if (!consultation) {
      return null;
    }

    resetFeedback();
    setLoading(true);

    try {
      const refreshedConsultation = await getConsultationSession(
        consultation.session_id,
      );
      setConsultation(mergeConsultationWithCurrentTurnBundle(refreshedConsultation));
      return refreshedConsultation;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "刷新失败");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function refreshConsultationMultimodalLive() {
    if (!consultation) {
      return null;
    }

    try {
      const live = await getConsultationMultimodalLive(consultation.session_id);
      applyConsultationMultimodalLive(live);
      return live;
    } catch {
      return null;
    }
  }

  function applyConsultationMultimodalLive(
    live: ConsultationMultimodalLive | ConsultationMultimodalLivePatch,
  ) {
    setConsultation((current) =>
      current
        ? {
            ...current,
            multimodal_live: mergeConsultationMultimodalLive(current.multimodal_live, live),
            multimodal_live_updated_at: live.updated_at || new Date().toISOString(),
          }
        : current,
    );
  }

  async function refreshAssessmentMultimodalLive() {
    if (!assessment) {
      return null;
    }

    try {
      const live = await getAssessmentMultimodalLive(assessment.session_id);
      setAssessment((current) =>
        current
          ? {
              ...current,
              multimodal_live: mergeConsultationMultimodalLive(current.multimodal_live, live),
              multimodal_live_updated_at: live.updated_at || new Date().toISOString(),
            }
          : current,
      );
      return live;
    } catch {
      return null;
    }
  }

  async function getConsultationTurnBundle(turnId: string) {
    if (!consultation) {
      return null;
    }

    try {
      const bundle = await getConsultationTurnMultimodalBundle(consultation.session_id, turnId);
      setConsultation((current) =>
        current && current.current_turn_id === turnId
          ? {
              ...current,
              current_turn_bundle: bundle,
            }
          : current,
      );
      return bundle;
    } catch (caught) {
      if (isMissingConsultationTurnBundleError(caught)) {
        return null;
      }
      setError(caught instanceof Error ? caught.message : "读取多模态汇总失败");
      return null;
    }
  }

  function mergeFrameCaptureResponseIntoConsultation(
    current: ConsultationSession,
    response: ConsultationFrameCaptureResponse,
    modality: "face" | "pose",
  ) {
    const nextLive = {
      ...(
        current.multimodal_live || {
          speech: { status: "pending" },
          text: { status: "pending" },
          face: { status: "pending" },
          pose: { status: "pending" },
          eeg_live: { status: "pending", latest_results: [] },
          eeg_waves: { status: "pending", samples: [] },
        }
      ),
    } as ConsultationMultimodalLive;
    const existing = (nextLive[modality] || { status: "pending" }) as ConsultationMultimodalLive["face"];
    const nextStatus =
      response.processing_status === "failed"
        ? "failed"
        : response.primary_label || response.processing_status === "completed"
          ? "ready"
          : existing.status || "pending";
    nextLive[modality] = {
      ...existing,
      status: nextStatus,
      processing_status: response.processing_status || existing.processing_status,
      primary_label: response.primary_label ?? existing.primary_label,
      primary_score: response.primary_score ?? existing.primary_score,
      top_3_labels: response.top_3_labels || existing.top_3_labels || [],
      quality_flags: response.quality_flags || existing.quality_flags || {},
      latest_capture_at: response.sample_ended_at ?? existing.latest_capture_at ?? null,
      sample_count: response.sample_count ?? existing.sample_count ?? null,
      valid_sample_count: response.valid_sample_count ?? existing.valid_sample_count ?? null,
      error_message: response.error_message ?? existing.error_message ?? null,
    };
    return {
      ...current,
      multimodal_live: nextLive,
      multimodal_live_updated_at: new Date().toISOString(),
      current_turn_bundle:
        response.turn_bundle && current.current_turn_id && response.turn_bundle.turn_id === current.current_turn_id
          ? response.turn_bundle
          : current.current_turn_bundle,
    };
  }

  function mergeVisualCaptureResponseIntoConsultation(response: ConsultationVisualCaptureResponse) {
    setConsultation((current) => {
      if (!current) {
        return current;
      }
      let next = current;
      if (response.face_result) {
        next = mergeFrameCaptureResponseIntoConsultation(next, response.face_result, "face");
      }
      if (response.pose_result) {
        next = mergeFrameCaptureResponseIntoConsultation(next, response.pose_result, "pose");
      }
      if (
        response.turn_bundle &&
        next.current_turn_id &&
        response.turn_bundle.turn_id === next.current_turn_id
      ) {
        next = {
          ...next,
          current_turn_bundle: response.turn_bundle,
        };
      }
      if (response.visual_pipeline) {
        next = {
          ...next,
          visual_pipeline: response.visual_pipeline,
        };
      }
      return next;
    });
  }

  async function submitConsultationVisualCapture(payload: ConsultationMultimodalCapturePayload) {
    if (!consultation) {
      return null;
    }

    try {
      const response = await submitConsultationVisualCaptureRequest(
        consultation.session_id,
        payload,
      );
      mergeVisualCaptureResponseIntoConsultation(response);
      return response;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "上传视觉采样失败");
      return null;
    }
  }

  async function completeConsultationSystemQuestionItem(questionKey: string) {
    if (!consultation) {
      return null;
    }

    resetFeedback();

    try {
      const updatedConsultation = await completeConsultationQuestionItem(
        consultation.session_id,
        questionKey,
      );
      return applyCompletedConsultationSystemQuestion(updatedConsultation);
    } catch (caught) {
      if (caught instanceof ApiRequestError && caught.status === 409) {
        try {
          const refreshedConsultation = await getConsultationSession(consultation.session_id);
          if (
            refreshedConsultation.current_question_key !== consultation.current_question_key ||
            refreshedConsultation.status !== consultation.status
          ) {
            return applyCompletedConsultationSystemQuestion(refreshedConsultation);
          }
        } catch {
          // Fall through to the regular error path below.
        }
      }
      setError(caught instanceof Error ? caught.message : "系统问题项推进失败");
      return null;
    }
  }

  function applyCompletedConsultationSystemQuestion(updatedConsultation: ConsultationSession) {
    setConsultation(mergeConsultationWithCurrentTurnBundle(updatedConsultation));
    setError("");
    if (updatedConsultation.status === "waiting_user_input") {
      setMessage("");
    } else if (updatedConsultation.status === "handoff_ready") {
      setMessage("问诊已完成");
    } else if (updatedConsultation.status === "paused_for_human_review") {
      setMessage("");
      setError("系统已触发高风险人工复核，标准问诊主链已暂停。");
    } else {
      setMessage("");
    }
    return updatedConsultation;
  }

  async function prefetchConsultationSystemQuestionItem(questionKey: string) {
    if (!consultation) {
      return null;
    }

    try {
      return await previewConsultationQuestionItemCompletion(consultation.session_id, questionKey);
    } catch (caught) {
      if (caught instanceof ApiRequestError && caught.status === 409) {
        try {
          const refreshedConsultation = await getConsultationSession(consultation.session_id);
          if (
            refreshedConsultation.current_question_key !== consultation.current_question_key ||
            refreshedConsultation.status !== consultation.status
          ) {
            return refreshedConsultation;
          }
        } catch {
          // Fall through to the regular error path below.
        }
      }
      throw caught;
    }
  }

  async function handleStartAssessment() {
    if (!consultation) {
      return null;
    }

    resetFeedback();

    if (consultation.status !== "handoff_ready") {
      setError(
        consultation.status === "paused_for_human_review"
          ? "当前问诊正在等待人工复核，暂时不能进入量表评估。"
          : "当前问诊尚未完成，暂时不能进入量表评估。",
      );
      return null;
    }

    setLoading(true);

    try {
      const assessmentSession = await createAssessmentSession({
        encounter_session_id: consultation.encounter_session_id || null,
        source_consultation_flow_run_id: consultation.session_id,
        multimodal_session_id: consultation.multimodal_session_id || null,
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
      const response = await submitAssessmentAnswer(assessment.session_id, {
        item_id: assessment.current_item?.item_id,
        selected_option_score: selectedAssessmentScore,
        raw_input: assessmentRawInput || null,
      });
      const updatedAssessment = response.assessment_session;

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

  function applyAssessmentSession(nextAssessment: AssessmentSession) {
    setAssessment(nextAssessment);
    saveAssessmentSessionId(nextAssessment.session_id);
  }

  async function submitAssessmentAnswerDetailed(payload: SubmitAssessmentAnswerPayload): Promise<{
    assessment_session: AssessmentSession;
    accepted_answer?: AssessmentAcceptedAnswer | null;
  }> {
    if (!assessment) {
      throw new Error("当前没有可提交的量表会话。");
    }

    resetFeedback();
    setLoading(true);

    try {
      return await submitAssessmentAnswer(assessment.session_id, payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "提交量表答案失败");
      throw caught;
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
    clearPersistedFlowState();
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
      savePreparationState,
      handleStartConsultation,
      submitConsultationTurn,
      submitManualConsultationTurn,
      refreshConsultation,
      refreshConsultationMultimodalLive,
      applyConsultationMultimodalLive,
      refreshAssessmentMultimodalLive,
      getConsultationTurnBundle,
      submitConsultationVisualCapture,
      completeConsultationSystemQuestionItem,
      applyCompletedConsultationSystemQuestion,
      prefetchConsultationSystemQuestionItem,
      handleStartAssessment,
      handleSubmitAssessment,
      applyAssessmentSession,
      submitAssessmentAnswerDetailed,
      refreshAssessment,
      handleLogout,
    },
  };
}

export type ConsultationAppStore = ReturnType<typeof useConsultationApp>;
