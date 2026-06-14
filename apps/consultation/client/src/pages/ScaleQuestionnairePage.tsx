import { useEffect, useEffectEvent, useMemo, useRef, useState, type CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
  PlayCircle,
  VideoOff,
} from "lucide-react";

import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { AppToast } from "../components/AppToast";
import { CameraPreview } from "../components/CameraPreview";
import { ConsultationProgress } from "../components/ConsultationProgress";
import { ConsultationStatusPanel } from "../components/ConsultationStatusPanel";
import { DraggableMessagePanel } from "../components/DraggableMessagePanel";
import { FlowCompletionState } from "../components/FlowCompletionState";
import { FloatingControlBar } from "../components/FloatingControlBar";
import {
  SeamlessVideoPlayer,
  type SeamlessVideoErrorEvent,
  type SeamlessVideoPlayerHandle,
  type SeamlessVideoTimeUpdateEvent,
} from "../components/video";
import { ConsultationLayout } from "../layouts";
import {
  buildAssessmentCurrentVideoNode,
  createAssessmentVideoNodeTransitionAdapter,
  isAssessmentStageIntroVideoNode,
  resolveMissingVideoNodeFallback,
  useVideoNodeTransitionController,
} from "../features/video-node";
import { buildRecordingFilename, formatDuration } from "../lib/mediaCapture";
import {
  buildScaleAssessmentPreviewStages,
  type ScaleAssessmentPreviewStage,
} from "../lib/scaleAssessmentPlaylist";
import { useMultimodalAudioSubmission } from "../lib/useMultimodalAudioSubmission";
import { useAudioRecording, type RecordingCompletedPayload } from "../lib/useAudioRecording";
import { useCamera } from "../lib/useCamera";
import { useJsonEventStream } from "../lib/useJsonEventStream";
import { mergeConsultationMultimodalLive } from "../lib/multimodalLiveMerge";
import { useMultimodalSession } from "../lib/useMultimodalSession";
import { useTimedToast } from "../lib/useTimedToast";
import { useVisualCapture } from "../lib/useVisualCapture";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";
import { ApiRequestError } from "../services/api/client";
import type { AssessmentAcceptedAnswer, ConsultationVisualCaptureResponse } from "../services/api/contracts";
import {
  getAssessmentMultimodalLive,
  getAssessmentMultimodalLiveStreamUrl,
  getAssessmentTurnMultimodalBundle,
} from "../services/api/assessment.api";
import {
  uploadMultimodalAudioTurn,
  uploadMultimodalVisualCapture,
} from "../services/api/multimodal.api";
import type {
  AssessmentOption,
  AssessmentSession,
  ConsultationMultimodalLive,
  ConsultationMultimodalLivePatch,
  ConsultationSession,
  ConsultationTurnMultimodalBundle,
  VisualPipelineStatus,
} from "../types";

const OPTION_LABELS = ["A", "B", "C", "D", "E", "F"];
const OPTION_BADGE_STYLES = [
  {
    inactive: "border border-sky-300/35 bg-sky-400/18 text-sky-50",
    active: "border border-sky-200/60 bg-sky-300 text-slate-950 shadow-[0_0_18px_rgba(125,211,252,0.35)]",
  },
  {
    inactive: "border border-emerald-300/35 bg-emerald-400/18 text-emerald-50",
    active: "border border-emerald-200/60 bg-emerald-300 text-slate-950 shadow-[0_0_18px_rgba(110,231,183,0.35)]",
  },
  {
    inactive: "border border-amber-300/35 bg-amber-400/18 text-amber-50",
    active: "border border-amber-200/60 bg-amber-300 text-slate-950 shadow-[0_0_18px_rgba(252,211,77,0.35)]",
  },
  {
    inactive: "border border-rose-300/35 bg-rose-400/18 text-rose-50",
    active: "border border-rose-200/60 bg-rose-300 text-slate-950 shadow-[0_0_18px_rgba(253,164,175,0.35)]",
  },
  {
    inactive: "border border-violet-300/35 bg-violet-400/18 text-violet-50",
    active: "border border-violet-200/60 bg-violet-300 text-slate-950 shadow-[0_0_18px_rgba(196,181,253,0.35)]",
  },
  {
    inactive: "border border-cyan-300/35 bg-cyan-400/18 text-cyan-50",
    active: "border border-cyan-200/60 bg-cyan-300 text-slate-950 shadow-[0_0_18px_rgba(103,232,249,0.35)]",
  },
] as const;
const ANSWER_CONFIRMATION_MS = 800;
const LIVE_REFRESH_INTERVAL_MS = 1000;
const VIDEO_COMPLETION_SCHEDULE_THRESHOLD_SECONDS = 0.9;
const VIDEO_COMPLETION_FALLBACK_BUFFER_MS = 120;

function formatStageQuestionCounter(current: number, total: number) {
  return `第 ${current}/${total} 题`;
}

function padQuestionNumber(order: number) {
  return String(order).padStart(3, "0");
}

function sleep(ms: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function buildPendingLive(): ConsultationMultimodalLive {
  return {
    speech: { status: "pending", top_3_labels: [] },
    text: { status: "pending", top_3_labels: [], negative_terms: [] },
    face: { status: "pending", top_3_labels: [], quality_flags: {}, latest_capture_at: null },
    pose: { status: "pending", top_3_labels: [], quality_flags: {}, latest_capture_at: null },
    eeg_live: {
      status: "pending",
      device_status: "pending",
      channel_names: ["T7", "T8", "Fpz"],
      sampling_rate: 500,
      latest_results: [],
    },
    eeg_waves: {
      status: "pending",
      channel_names: ["T7", "T8", "Fpz"],
      sampling_rate: 500,
      samples: [],
    },
    updated_at: null,
  };
}

function mergeVisualCaptureLive(
  current: ConsultationMultimodalLive | null,
  response: ConsultationVisualCaptureResponse,
) {
  const next = current ? { ...current } : buildPendingLive();

  if (response.face_result) {
    next.face = {
      ...(next.face || { status: "pending", top_3_labels: [], quality_flags: {}, latest_capture_at: null }),
      status:
        response.face_result.processing_status === "failed"
          ? "failed"
          : response.face_result.primary_label || response.face_result.processing_status === "completed"
            ? "ready"
            : "pending",
      processing_status: response.face_result.processing_status || null,
      primary_label: response.face_result.primary_label ?? null,
      primary_score: response.face_result.primary_score ?? null,
      top_3_labels: response.face_result.top_3_labels || [],
      quality_flags: response.face_result.quality_flags || {},
      latest_capture_at: response.face_result.sample_ended_at ?? null,
      sample_count: response.face_result.sample_count ?? null,
      valid_sample_count: response.face_result.valid_sample_count ?? null,
      error_message: response.face_result.error_message ?? null,
    };
  }

  if (response.pose_result) {
    next.pose = {
      ...(next.pose || { status: "pending", top_3_labels: [], quality_flags: {}, latest_capture_at: null }),
      status:
        response.pose_result.processing_status === "failed"
          ? "failed"
          : response.pose_result.primary_label || response.pose_result.processing_status === "completed"
            ? "ready"
            : "pending",
      processing_status: response.pose_result.processing_status || null,
      primary_label: response.pose_result.primary_label ?? null,
      primary_score: response.pose_result.primary_score ?? null,
      top_3_labels: response.pose_result.top_3_labels || [],
      quality_flags: response.pose_result.quality_flags || {},
      latest_capture_at: response.pose_result.sample_ended_at ?? null,
      sample_count: response.pose_result.sample_count ?? null,
      valid_sample_count: response.pose_result.valid_sample_count ?? null,
      error_message: response.pose_result.error_message ?? null,
    };
  }

  next.updated_at = new Date().toISOString();
  return next;
}

function buildAssessmentVideoNodeFromSession({
  assessmentSession,
  previewStages,
  playedStageIntros,
}: {
  assessmentSession: AssessmentSession | null;
  previewStages: ScaleAssessmentPreviewStage[];
  playedStageIntros: Record<string, boolean>;
}) {
  const currentScaleSlug = assessmentSession?.current_scale_slug || null;
  const currentItem = assessmentSession?.current_item || null;
  if (!assessmentSession || !currentScaleSlug || !currentItem) {
    return null;
  }

  const currentStage = previewStages.find((stage) => stage.slug === currentScaleSlug) || null;
  if (!currentStage) {
    return null;
  }

  const currentQuestionOrder = currentItem.index || assessmentSession.current_item_index || 1;
  const currentQuestionKey = `${currentScaleSlug}-${padQuestionNumber(currentQuestionOrder)}`;
  const currentQuestion =
    currentStage.questions.find((question) => question.questionKey === currentQuestionKey) ||
    currentStage.questions.find((question) => question.order === currentQuestionOrder) ||
    null;
  const hasPendingStageIntro = Boolean(
    currentStage.introText &&
      currentStage.introVideoUri &&
      currentQuestionOrder === 1 &&
      !playedStageIntros[currentStage.slug],
  );

  return buildAssessmentCurrentVideoNode({
    currentStage,
    currentQuestion,
    currentQuestionKey,
    currentItem,
    hasPendingStageIntro,
  });
}

export default function ScaleQuestionnairePage() {
  const navigate = useNavigate();
  const { state, actions } = useConsultationAppContext();
  const assessment = state.assessment;
  const consultation = state.consultation;
  const { toast, pushToast } = useTimedToast();

  const [isOpen, setIsOpen] = useState(false);
  const [isScaleOpen, setIsScaleOpen] = useState(true);
  const [playbackBlocked, setPlaybackBlocked] = useState(false);
  const [videoError, setVideoError] = useState("");
  const [videoFinished, setVideoFinished] = useState(false);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [isAdvancingAfterConfirmation, setIsAdvancingAfterConfirmation] = useState(false);
  const [subtitleUserTranscript, setSubtitleUserTranscript] = useState<string | null>(null);
  const [pendingAcceptedAnswer, setPendingAcceptedAnswer] = useState<AssessmentAcceptedAnswer | null>(null);
  const [multimodalLive, setMultimodalLive] = useState<ConsultationMultimodalLive | null>(null);
  const [currentTurnBundle, setCurrentTurnBundle] = useState<ConsultationTurnMultimodalBundle | null>(null);
  const [visualPipeline, setVisualPipeline] = useState<VisualPipelineStatus | null>(null);
  const [playedStageIntros, setPlayedStageIntros] = useState<Record<string, boolean>>({});

  const { cameraReady, cameraStream, cameraError, cameraFeedback } = useCamera({ enabled: true });
  const isUnmountingRef = useRef(false);
  const { submitRecordedAudio } = useMultimodalAudioSubmission();

  const playerRef = useRef<SeamlessVideoPlayerHandle | null>(null);
  const cameraVideoRef = useRef<HTMLVideoElement | null>(null);
  const lastRecordingUrlRef = useRef<string | null>(null);
  const liveRefreshInFlightRef = useRef(false);
  const videoCompletionTimerRef = useRef<number | null>(null);
  const videoCompletionScheduledClipKeyRef = useRef<string | null>(null);
  const completedVideoClipKeyRef = useRef<string | null>(null);

  const previewStages = useMemo(
    () => buildScaleAssessmentPreviewStages(state.assessmentCatalog),
    [state.assessmentCatalog],
  );
  const scaleSteps = useMemo(() => previewStages.map((stage) => stage.stageLabel), [previewStages]);

  const currentScaleSlug = assessment?.current_scale_slug || null;
  const currentItem = assessment?.current_item || null;
  const currentStage = useMemo(
    () => previewStages.find((stage) => stage.slug === currentScaleSlug) || null,
    [currentScaleSlug, previewStages],
  );
  const currentQuestionOrder = currentItem?.index || 1;
  const currentQuestionKey = useMemo(() => {
    if (!currentScaleSlug) {
      return null;
    }
    return `${currentScaleSlug}-${padQuestionNumber(currentQuestionOrder)}`;
  }, [currentQuestionOrder, currentScaleSlug]);
  const linkedMultimodalSessionId =
    assessment?.multimodal_session_id || consultation?.multimodal_session_id || null;
  const { ensureSession: ensureMultimodalSession, clearSession: clearMultimodalSession } =
    useMultimodalSession({
      linkedSessionId: linkedMultimodalSessionId,
      missingSessionMessage: "量表阶段缺少可复用的多模态会话，请先回到数字人问诊入口重新开始。",
    });

  const {
    isActive: isLiveStreamActive,
    activeRef: liveStreamActiveRef,
  } = useJsonEventStream<ConsultationMultimodalLivePatch>({
    url:
      assessment?.session_id && typeof window !== "undefined"
        ? getAssessmentMultimodalLiveStreamUrl(assessment.session_id)
        : null,
    onMessage: (live) => {
      setMultimodalLive((current) => mergeConsultationMultimodalLive(current, live));
    },
  });

  const currentQuestion = useMemo(() => {
    if (!currentStage) {
      return null;
    }
    return (
      currentStage.questions.find((question) => question.questionKey === currentQuestionKey) ||
      currentStage.questions.find((question) => question.order === currentQuestionOrder) ||
      null
    );
  }, [currentQuestionKey, currentQuestionOrder, currentStage]);
  const currentStageQuestionCount = currentStage?.questions.length || 0;
  const currentStageOrder = currentStage?.stageOrder || 1;
  const currentOptions = currentItem?.answer_options?.length
    ? currentItem.answer_options
    : currentStage?.answerOptions || [];
  const currentQuestionText = currentQuestion?.questionText || currentItem?.text || "";
  const hasPendingStageIntro = Boolean(
    currentStage?.introText &&
      currentStage?.introVideoUri &&
      currentQuestionOrder === 1 &&
      !playedStageIntros[currentStage.slug],
  );
  const assessmentCurrentVideoNode = useMemo(
    () =>
      buildAssessmentCurrentVideoNode({
        currentStage,
        currentQuestion,
        currentQuestionKey,
        currentItem,
        hasPendingStageIntro,
      }),
    [currentItem, currentQuestion, currentQuestionKey, currentStage, hasPendingStageIntro],
  );
  const currentQuestionVideoNode = useMemo(
    () =>
      buildAssessmentCurrentVideoNode({
        currentStage,
        currentQuestion,
        currentQuestionKey,
        currentItem,
        hasPendingStageIntro: false,
      }),
    [currentItem, currentQuestion, currentQuestionKey, currentStage],
  );
  const assessmentTransitionAdapter = createAssessmentVideoNodeTransitionAdapter({
    currentNode: assessmentCurrentVideoNode,
    previewLocalNextNode: (videoNode) => {
      if (!isAssessmentStageIntroVideoNode(videoNode)) {
        return null;
      }

      return currentQuestionVideoNode;
    },
    deriveNextNodeFromAssessmentSession: (assessmentSession) =>
      buildAssessmentVideoNodeFromSession({
        assessmentSession,
        previewStages,
        playedStageIntros,
      }),
  });
  const {
    state: videoTransitionState,
    currentClip,
    preloadClip,
    requestPreview,
    primeNextNodeFromResult,
    markReadyClip,
    markDisplayedClip,
    handleClipLoadError,
  } = useVideoNodeTransitionController({
    adapter: assessmentTransitionAdapter,
  });
  const currentVideoNode = assessmentCurrentVideoNode;
  const isCurrentVideoStageIntro = isAssessmentStageIntroVideoNode(currentVideoNode);
  const missingVideoFallback = useMemo(
    () => resolveMissingVideoNodeFallback(currentVideoNode),
    [currentVideoNode],
  );
  const currentPromptText = currentVideoNode?.displayText || currentQuestionText;
  const currentVideoAssetId = currentVideoNode?.videoAssetId || currentQuestionKey;
  const currentVideoUri = currentVideoNode?.videoUri || null;
  const playableVideoUri = currentClip?.src ?? null;
  const currentTurnId = currentQuestionKey;
  const isAssessmentCompleted = assessment?.status === "completed";

  function clearVideoCompletionFallback() {
    if (videoCompletionTimerRef.current !== null) {
      window.clearTimeout(videoCompletionTimerRef.current);
      videoCompletionTimerRef.current = null;
    }
    videoCompletionScheduledClipKeyRef.current = null;
  }

  const activeAcceptedScore =
    pendingAcceptedAnswer?.question_key === currentQuestionKey
      ? pendingAcceptedAnswer.selected_option_score ?? null
      : null;
  const activeAcceptedLabel =
    pendingAcceptedAnswer?.question_key === currentQuestionKey
      ? pendingAcceptedAnswer.selected_option_label ?? null
      : null;

  const handleAudioRecordingComplete = useEffectEvent(
    async (payload: RecordingCompletedPayload) => {
    const { blob } = payload;

    const objectUrl = URL.createObjectURL(blob);
    if (lastRecordingUrlRef.current) {
      URL.revokeObjectURL(lastRecordingUrlRef.current);
    }
    lastRecordingUrlRef.current = objectUrl;

    setIsSubmittingAnswer(true);

    try {
      if (!assessment || !currentQuestionKey || !currentStage || !currentItem) {
        throw new Error("当前题目缺少语音答题上下文，请刷新后重试。");
      }
      const submittedAudio = await submitRecordedAudio({
        payload,
        context: {
          assessment,
          currentQuestionKey,
          currentStageSlug: currentStage.slug,
          currentTurnId,
        },
        ensureSession: ensureMultimodalSession,
        emptyRecordingMessage: "本轮录音内容为空，请重新录音或直接点击选项。",
        emptyTranscriptMessage: "Dolphin 未返回有效转写文本，请重新录音。",
        uploadAudioTurn: async ({
          sessionId,
          blob: audioBlob,
          resolvedMimeType,
          durationMs,
          startedAtIso,
          completedAtIso,
          context,
        }) =>
          uploadMultimodalAudioTurn(sessionId, {
            flow_run_id: context.assessment.session_id,
            origin_flow_type: "assessment",
            question_key: context.currentQuestionKey,
            stage_id: context.currentStageSlug,
            node_id: context.currentQuestionKey,
            duration_ms: durationMs,
            response_started_at: startedAtIso,
            response_completed_at: completedAtIso,
            mime_type: resolvedMimeType,
            turn_id: context.currentTurnId,
            audio_file: audioBlob,
            filename: buildRecordingFilename(context.currentQuestionKey, resolvedMimeType),
          }),
      });

      setSubtitleUserTranscript(submittedAudio.transcriptText);
      await captureSupplementalFrame(currentTurnId).catch(() => undefined);
      await refreshAssessmentMultimodalArtifacts();

      const response = await actions.submitAssessmentAnswerDetailed({
        item_id: currentItem.item_id,
        question_key: currentQuestionKey,
        turn_id: currentTurnId,
        answer_source: "voice",
        raw_input: submittedAudio.transcriptText,
        transcript_text: submittedAudio.transcriptText,
        transcript_source: "dolphin_final",
        audio_uri: submittedAudio.transcriptReadyAudioTurn.audio_uri,
        normalized_wav_uri: submittedAudio.transcriptReadyAudioTurn.normalized_wav_uri || null,
        multimodal_session_id: submittedAudio.sessionId,
        response_started_at: submittedAudio.startedAtIso,
        response_completed_at: submittedAudio.completedAtIso,
        capture_timestamp: submittedAudio.completedAtIso,
      });

      await refreshAssessmentMultimodalArtifacts();
      await applyAcceptedAnswer(response, "voice");
    } catch (caught) {
      if (caught instanceof ApiRequestError && caught.status === 422) {
        pushToast("未能识别出对应选项，请改用点击选择或更明确地回答", "error", {
          durationMs: 5000,
        });
      } else {
        const message = caught instanceof Error ? caught.message : "语音答题失败，请重新录音。";
        pushToast(message, "error");
      }
    } finally {
      setIsSubmittingAnswer(false);
    }
  },
);

  const {
    isRecording,
    recordingElapsedMs,
    microphoneFeedback,
    startRecording,
    stopRecording,
  } = useAudioRecording({
    onRecordingComplete: handleAudioRecordingComplete,
    onError: (msg: string) => pushToast(msg, "error"),
    isUnmountingRef,
  });

  const canAnswerCurrentQuestion =
    Boolean(assessment && currentQuestionKey && videoFinished) &&
    !isAssessmentCompleted &&
    !isRecording &&
    !isSubmittingAnswer &&
    !isAdvancingAfterConfirmation;

  const applyVisualCaptureResponse = useEffectEvent((response: ConsultationVisualCaptureResponse) => {
    setMultimodalLive((current) => mergeVisualCaptureLive(current, response));
    if (response.turn_bundle) {
      setCurrentTurnBundle(response.turn_bundle);
    }
    if (response.visual_pipeline) {
      setVisualPipeline(response.visual_pipeline);
    }
  });

  const { captureNow: captureSupplementalFrame, resetCaptureCount } = useVisualCapture<string | null>({
    enabled: cameraReady && !!currentTurnId && !!assessment && !isAssessmentCompleted,
    cameraStream,
    videoRef: cameraVideoRef,
    uploadFn: async ({ blob, sampleIndex, startedAt, endedAt, context }) => {
      if (!assessment || !currentQuestionKey || !currentStage) return;
      const ensuredSessionId = await ensureMultimodalSession();
      const imageFile = new File([blob], `assessment-capture-${sampleIndex}.jpg`, { type: blob.type || "image/jpeg" });
      const response = await uploadMultimodalVisualCapture(ensuredSessionId, {
        flow_run_id: assessment.session_id,
        origin_flow_type: "assessment",
        question_key: currentQuestionKey,
        stage_id: currentStage.slug,
        turn_id: context ?? currentTurnId ?? null,
        sample_started_at: startedAt,
        sample_ended_at: endedAt,
        sample_index: sampleIndex,
        mime_type: imageFile.type || "image/jpeg",
        image_file: imageFile,
      });
      applyVisualCaptureResponse(response);
    },
  });

  useEffect(() => {
    return () => {
      isUnmountingRef.current = true;
      clearVideoCompletionFallback();
      if (lastRecordingUrlRef.current) {
        URL.revokeObjectURL(lastRecordingUrlRef.current);
      }
    };
  }, []);

  useEffect(() => {
    clearMultimodalSession();
    setMultimodalLive(null);
    setCurrentTurnBundle(null);
    setVisualPipeline(null);
    setPlayedStageIntros({});
  }, [assessment?.session_id, clearMultimodalSession]);

  useEffect(() => {
    setSubtitleUserTranscript(null);
    setPendingAcceptedAnswer(null);
    setCurrentTurnBundle(null);
    setMultimodalLive(null);
    setVisualPipeline(null);
    resetCaptureCount();
  }, [currentQuestionKey, resetCaptureCount]);

  useEffect(() => {
    if (videoTransitionState.previewError) {
      pushToast(`下一段量表视频预热失败，切换时会回退到常规加载。${videoTransitionState.previewError}`, "warning");
    }
  }, [pushToast, videoTransitionState.previewError]);

  useEffect(() => {
    if (videoTransitionState.transitionReason === "commit_mismatch") {
      pushToast("预热结果与正式答题推进结果不一致，已按正式结果重新切换。", "warning");
    }
  }, [pushToast, videoTransitionState.transitionReason]);

  useEffect(() => {
    clearVideoCompletionFallback();
    completedVideoClipKeyRef.current = null;
    setPlaybackBlocked(false);
    setVideoError("");
    setVideoFinished(false);
  }, [currentClip?.clipKey]);

  useEffect(() => {
    if (!missingVideoFallback.isMissingVideo || !currentVideoNode) {
      return;
    }

    if (missingVideoFallback.behavior === "local_skip" && currentStage?.slug) {
      setPlayedStageIntros((current) =>
        current[currentStage.slug] ? current : { ...current, [currentStage.slug]: true },
      );
      return;
    }

    if (missingVideoFallback.behavior === "allow_response") {
      setVideoFinished((current) => (current ? current : true));
    }
  }, [
    currentStage?.slug,
    currentVideoNode,
    missingVideoFallback.behavior,
    missingVideoFallback.isMissingVideo,
  ]);

  async function refreshAssessmentMultimodalArtifacts() {
    if (!assessment?.session_id || !currentTurnId || liveRefreshInFlightRef.current) {
      return;
    }
    if (typeof document !== "undefined" && document.visibilityState === "hidden") {
      return;
    }

    liveRefreshInFlightRef.current = true;
    try {
      // Only fetch the bundle after the current turn has already produced one.
      // Otherwise, immediately switching to the next question can race ahead of
      // bundle creation and spam harmless-but-noisy 404s for the new turn.
      const shouldFetchBundle = currentTurnBundle?.turn_id === currentTurnId;
      const bundlePromise = shouldFetchBundle
        ? getAssessmentTurnMultimodalBundle(assessment.session_id, currentTurnId)
        : Promise.resolve<ConsultationTurnMultimodalBundle | null>(null);
      const livePromise = liveStreamActiveRef.current
        ? Promise.resolve<ConsultationMultimodalLive | null>(null)
        : getAssessmentMultimodalLive(assessment.session_id);
      const [live, bundle] = await Promise.allSettled([livePromise, bundlePromise]);

      if (live.status === "fulfilled" && live.value) {
        setMultimodalLive((current) => mergeConsultationMultimodalLive(current, live.value));
      }
      if (bundle.status === "fulfilled" && bundle.value) {
        setCurrentTurnBundle(bundle.value);
      } else if (
        bundle.status === "rejected" &&
        bundle.reason instanceof ApiRequestError &&
        bundle.reason.status === 404
      ) {
        return;
      }
    } finally {
      liveRefreshInFlightRef.current = false;
    }
  }

  useEffect(() => {
    if (!assessment || !currentStage || isAssessmentCompleted) {
      return;
    }

    void ensureMultimodalSession().catch(() => undefined);
  }, [assessment?.session_id, currentStage?.slug, ensureMultimodalSession, isAssessmentCompleted]);

  useEffect(() => {
    if (!assessment?.session_id || !currentTurnId || isAssessmentCompleted) {
      return;
    }

    void refreshAssessmentMultimodalArtifacts();
    const timer = window.setInterval(() => {
      void refreshAssessmentMultimodalArtifacts();
    }, LIVE_REFRESH_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [assessment?.session_id, currentTurnId, ensureMultimodalSession, isAssessmentCompleted]);

  async function handlePlayCurrentVideo() {
    const player = playerRef.current;
    if (!player) {
      return;
    }

    clearVideoCompletionFallback();
    completedVideoClipKeyRef.current = null;
    setPlaybackBlocked(false);
    setVideoError("");
    setVideoFinished(false);
    const displayedVideo = player.getDisplayedVideoElement();
    if (displayedVideo) {
      displayedVideo.currentTime = 0;
    }

    try {
      await player.playDisplayed();
    } catch {
      setPlaybackBlocked(true);
      pushToast("浏览器阻止了自动播放，请点击数字人区域中央的播放按钮继续。", "warning");
    }
  }

  const finalizeCurrentVideoPlayback = useEffectEvent(async () => {
    if (!currentVideoNode || !currentClip?.clipKey) {
      return;
    }

    if (completedVideoClipKeyRef.current === currentClip.clipKey) {
      return;
    }

    completedVideoClipKeyRef.current = currentClip.clipKey;
    clearVideoCompletionFallback();

    if (isAssessmentStageIntroVideoNode(currentVideoNode) && currentStage?.slug) {
      await requestPreview();
      setPlayedStageIntros((current) =>
        current[currentStage.slug] ? current : { ...current, [currentStage.slug]: true },
      );
      return;
    }

    setVideoFinished((current) => (current ? current : true));
  });

  async function handleVideoEnded() {
    await finalizeCurrentVideoPlayback();
  }

  function handleVideoTimeUpdate(event: SeamlessVideoTimeUpdateEvent) {
    const remainingSeconds = event.video.duration - event.video.currentTime;
    if (!Number.isFinite(remainingSeconds)) {
      return;
    }

    if (isCurrentVideoStageIntro && remainingSeconds <= VIDEO_COMPLETION_SCHEDULE_THRESHOLD_SECONDS) {
      void requestPreview();
    }

    if (
      !currentClip?.clipKey ||
      completedVideoClipKeyRef.current === currentClip.clipKey ||
      videoCompletionScheduledClipKeyRef.current === currentClip.clipKey ||
      remainingSeconds > VIDEO_COMPLETION_SCHEDULE_THRESHOLD_SECONDS
    ) {
      return;
    }

    clearVideoCompletionFallback();
    videoCompletionScheduledClipKeyRef.current = currentClip.clipKey;
    videoCompletionTimerRef.current = window.setTimeout(() => {
      void finalizeCurrentVideoPlayback();
    }, Math.max(Math.ceil(remainingSeconds * 1000) + VIDEO_COMPLETION_FALLBACK_BUFFER_MS, 0));
  }

  function handleVideoError(event: SeamlessVideoErrorEvent) {
    const clipKey = event.clip?.clipKey ?? null;
    const scope = handleClipLoadError(clipKey);
    if (scope === "prefetched") {
      pushToast("后台预热视频加载失败，提交答案后会按正式结果重新加载下一题。", "warning");
      return;
    }

    setVideoError("当前视频资源加载失败，请稍后重试。");
    setPlaybackBlocked(false);
  }

  async function applyAcceptedAnswer(
    response: {
      assessment_session: AssessmentSession | null;
      accepted_answer?: AssessmentAcceptedAnswer | null;
    },
    mode: "voice" | "click",
  ) {
    const acceptedAnswer = response.accepted_answer || null;
    if (acceptedAnswer) {
      setPendingAcceptedAnswer(acceptedAnswer);
      if (acceptedAnswer.transcript_text?.trim()) {
        setSubtitleUserTranscript(acceptedAnswer.transcript_text.trim());
      }
    }

    if (response.assessment_session) {
      primeNextNodeFromResult(response.assessment_session);
    }

    setIsAdvancingAfterConfirmation(true);
    if (mode === "voice") {
      pushToast("语音回答已识别完成，正在切换到下一题。", "success");
    }
    await sleep(ANSWER_CONFIRMATION_MS);

    if (response.assessment_session) {
      actions.applyAssessmentSession(response.assessment_session);
      if (response.assessment_session.status === "completed") {
        pushToast("量表阶段已完成，已生成聚合结果。", "success");
      }
    }

    setPendingAcceptedAnswer(null);
    setIsAdvancingAfterConfirmation(false);
  }

  async function handleSubmitClickAnswer(option: AssessmentOption) {
    if (!assessment || !currentQuestionKey || !currentItem || !canAnswerCurrentQuestion) {
      return;
    }

    setIsSubmittingAnswer(true);
    try {
      const response = await actions.submitAssessmentAnswerDetailed({
        item_id: currentItem.item_id,
        question_key: currentQuestionKey,
        turn_id: currentTurnId,
        answer_source: "click_selection",
        selected_option_label: option.label,
        selected_option_score: option.score,
        raw_input: option.label,
        transcript_source: "click_selection",
        multimodal_session_id: linkedMultimodalSessionId,
        capture_timestamp: new Date().toISOString(),
      });
      await applyAcceptedAnswer(response, "click");
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "提交量表答案失败";
      pushToast(message, "error");
    } finally {
      setIsSubmittingAnswer(false);
    }
  }

  async function handleToggleRecord() {
    if (!assessment || isAssessmentCompleted) {
      return;
    }

    if (isSubmittingAnswer || state.loading) {
      return;
    }

    if (isRecording) {
      stopRecording();
      return;
    }

      if (!videoFinished) {
        pushToast(
          isCurrentVideoStageIntro ? "请先听完当前阶段的引导视频。" : "请先听完当前题目的视频播报，再开始语音回答。",
          "warning",
        );
        return;
      }

    if (isAdvancingAfterConfirmation) {
      return;
    }

    await startRecording();
  }

  async function handleRefresh() {
    await Promise.allSettled([
      actions.refreshAssessment(),
      actions.refreshConsultation(),
      refreshAssessmentMultimodalArtifacts(),
    ]);
  }

  function handleEnd() {
    navigate(APP_PATHS.result);
  }

  const assistantLines = useMemo(() => {
    if (isAssessmentCompleted) {
      return ["系统：量表阶段已经完成，可以进入结果页查看评估结果。"];
    }
    if (!assessment || !currentPromptText) {
      return ["数字人：量表会话尚未加载。"];
    }

    const lines = [`数字人：${currentPromptText}`];

    if (subtitleUserTranscript?.trim()) {
      lines.push(`用户：${subtitleUserTranscript.trim()}`);
    } else if (isSubmittingAnswer) {
      lines.push("用户：（Dolphin 正在转写并匹配当前量表选项）");
    } else if (isRecording) {
      lines.push(`用户：（录音中 ${formatDuration(recordingElapsedMs)}）`);
    } else if (missingVideoFallback.isMissingVideo) {
      lines.push(`系统：${missingVideoFallback.description}`);
    } else if (!videoFinished) {
      lines.push(isCurrentVideoStageIntro ? "系统：请先听完当前阶段的引导视频。" : "系统：请先听完当前题目的视频播报。");
    } else if (isAdvancingAfterConfirmation && activeAcceptedLabel) {
      lines.push(`系统：已确认选项「${activeAcceptedLabel}」，正在进入下一题。`);
    } else {
      lines.push("系统：现在可以语音回答，也可以点击左侧量表选项。");
    }

    return lines;
  }, [
    activeAcceptedLabel,
    assessment,
    currentPromptText,
    isCurrentVideoStageIntro,
    isAdvancingAfterConfirmation,
    isAssessmentCompleted,
    isRecording,
    isSubmittingAnswer,
    missingVideoFallback.description,
    missingVideoFallback.isMissingVideo,
    recordingElapsedMs,
    subtitleUserTranscript,
    videoFinished,
  ]);

  const stageSummaryText = useMemo(() => {
    if (!currentStage || !currentItem || isAssessmentCompleted) {
      return isAssessmentCompleted ? "量表流程已完成" : "";
    }
    if (isCurrentVideoStageIntro) {
      return `${currentStage.stageLabel} · 阶段引导`;
    }
    return `${currentStage.stageLabel} · ${formatStageQuestionCounter(currentItem.index, currentStageQuestionCount)}`;
  }, [currentItem, currentStage, currentStageQuestionCount, isAssessmentCompleted, isCurrentVideoStageIntro]);

  const responseWindowStatusText = useMemo(() => {
    if (isAssessmentCompleted) {
      return "量表流程已完成，可以查看结果页。";
    }
    if (!assessment || !currentStage || !currentItem) {
      return "量表会话尚未加载。";
    }
    if (videoError) {
      return "当前视频加载失败，请尝试重播当前题目。";
    }
    if (isSubmittingAnswer) {
      return "正在提交当前题目的量表答案，多模态结果会继续补齐。";
    }
    if (isAdvancingAfterConfirmation) {
      return "当前答案已确认，正在推进到下一题。";
    }
    if (isRecording) {
      return `录音中 ${formatDuration(recordingElapsedMs)}，结束录音后会自动转写并匹配量表选项。`;
    }
    if (missingVideoFallback.isMissingVideo) {
      return missingVideoFallback.description;
    }
    if (!videoFinished) {
      return isCurrentVideoStageIntro
        ? `正在播报 ${currentStage.stageLabel} 的阶段引导，请先听完再开始答题。`
        : `正在播报 ${currentStage.stageLabel} 第 ${currentItem.index} 题。`;
    }
    return `当前可以通过语音回答或点击左侧选项答题。时间范围：${currentStage.timeframe}。`;
  }, [
    assessment,
    currentItem,
    currentStage,
    isCurrentVideoStageIntro,
    isAdvancingAfterConfirmation,
    isAssessmentCompleted,
    isRecording,
    isSubmittingAnswer,
    missingVideoFallback.description,
    missingVideoFallback.isMissingVideo,
    recordingElapsedMs,
    videoError,
    videoFinished,
  ]);

  const synthesizedConsultation = useMemo<ConsultationSession | null>(() => {
    if (!assessment || !currentStage || !currentQuestionKey || !currentVideoNode || isAssessmentCompleted) {
      return null;
    }

    return {
      session_id: assessment.session_id,
      encounter_session_id: assessment.encounter_session_id || null,
      user_id: assessment.user_id,
      workflow_id: "scale-assessment-v1",
      current_stage_id: currentStage.slug,
      current_node_id: currentVideoNode.nodeKey,
      current_question_key: currentVideoNode.questionKey || currentQuestionKey,
      current_question_order: currentItem?.index || 1,
      current_question_video_asset_id: currentVideoAssetId,
      current_question_video_uri: currentVideoUri,
      current_question_text: currentPromptText,
      current_question_subtitle_text: currentVideoNode.subtitleText,
      current_stage: {
        stage_id: currentStage.slug,
        stage_label: currentStage.stageLabel,
        stage_order: currentStage.stageOrder,
        total_stages: scaleSteps.length || 1,
      },
      status: isSubmittingAnswer
        ? "processing_response"
        : isRecording
          ? "recording_response"
          : videoFinished
            ? "waiting_user_input"
            : "waiting_system_completion",
      current_turn_id: currentTurnId,
      current_question_item: {
        question_key: currentVideoNode.questionKey || currentQuestionKey,
        stage_id: currentStage.slug,
        stage_label: currentStage.stageLabel,
        stage_order: currentStage.stageOrder,
        order: currentItem?.index || 1,
        node_id: currentVideoNode.nodeKey,
        video_asset_id: currentVideoAssetId,
        video_uri: currentVideoUri,
        question_text: currentPromptText,
        subtitle_text: currentVideoNode.subtitleText,
        response_required: currentVideoNode.responseRequired,
      },
      current_prompt: currentPromptText,
      required_scales: assessment.required_scales,
      multimodal_session_id: linkedMultimodalSessionId,
      multimodal_live: multimodalLive || undefined,
      current_turn_bundle: currentTurnBundle || undefined,
      visual_pipeline: visualPipeline || undefined,
      subtitle_history: [],
      current_doctor_persona: undefined,
      completed_stages: [],
      scale_handoff_payload: undefined,
      engine_state: undefined,
      device_status: {},
      participant_profile_snapshot: {},
      created_at: "",
      updated_at: "",
    } as unknown as ConsultationSession;
  }, [
    assessment,
    currentStage,
    currentQuestionKey,
    currentItem,
    currentVideoNode,
    currentVideoUri,
    currentPromptText,
    currentVideoAssetId,
    currentTurnId,
    isAssessmentCompleted,
    isRecording,
    isSubmittingAnswer,
    videoFinished,
    linkedMultimodalSessionId,
    multimodalLive,
    currentTurnBundle,
    visualPipeline,
    scaleSteps,
  ]);

  const microphoneStatusTitle =
    isRecording ? "正在录音中" + (recordingElapsedMs > 0 ? ` ${formatDuration(recordingElapsedMs)}` : "")
    : microphoneFeedback?.title || "麦克风未激活";

  if (isAssessmentCompleted) {
    return (
      <ConsultationLayout backgroundImage="/4K.png" title="智能评估">
        <div className="absolute inset-x-0 top-0 z-50 pointer-events-none">
          <div className="pointer-events-auto">
            <ConsultationProgress currentStageOrder={scaleSteps.length} steps={scaleSteps} />
          </div>
        </div>
        <FlowCompletionState
          title="量表流程已完成"
          description="多模态聚合结果已生成，可以进入结果页查看评估结果。"
          actionLabel="进入结果页"
          onAction={handleEnd}
        />
      </ConsultationLayout>
    );
  }

  if (!assessment || !currentStage || !currentItem) {
    return (
      <ConsultationLayout backgroundImage="/4K.png" title="智能评估">
        <div className="flex h-full w-full items-center justify-center px-6">
          <div className="w-full max-w-xl rounded-[2rem] border border-white/20 bg-slate-950/35 px-8 py-10 text-center text-white shadow-[0_25px_80px_rgba(15,23,42,0.28)] backdrop-blur-xl">
            <LoaderCircle className="mx-auto mb-4 h-8 w-8 animate-spin text-sky-200" />
            <p className="text-lg font-medium">{state.loading ? "正在恢复量表会话..." : "当前没有可继续的量表会话。"}</p>
            <p className="mt-3 text-sm text-slate-200/75">请从问诊页进入量表阶段。</p>
            <button
              onClick={() => navigate(APP_PATHS.home)}
              className="mt-6 rounded-full border border-white/25 bg-white/10 px-5 py-2 text-sm text-white transition hover:bg-white/18"
            >
              返回首页
            </button>
          </div>
        </div>
      </ConsultationLayout>
    );
  }

  return (
    <ConsultationLayout backgroundImage="/4K.png" title="智能评估">
      <div className="absolute inset-x-0 top-0 z-50 pointer-events-none">
        <div className="pointer-events-auto">
          <ConsultationProgress currentStageOrder={currentStageOrder} steps={scaleSteps} />
        </div>
      </div>

      <AppToast toast={toast} />

      <div
        style={{
          "--scale-panel-width": "clamp(260px, 22vw, 340px)",
          "--scale-panel-left": "clamp(12px, 2vw, 32px)",
          "--scale-visual-width": "calc(var(--scale-panel-width) * 0.966)",
          "--scale-total-offset": "calc(var(--scale-panel-left) + var(--scale-visual-width))",
          "--results-panel-reserve": "min(46vw, 670px)",
          "--results-panel-shift": "calc(var(--results-panel-reserve) / 2)",
        } as CSSProperties}
        className="flex w-full h-full relative z-10 bg-transparent pt-8 overflow-hidden [perspective:2000px]"
      >
        <div
          className="flex-1 relative h-full flex flex-col items-center transition-all duration-[800ms] min-h-0 min-w-0 perspective-[1200px]"
          style={{
            marginLeft: isScaleOpen ? "var(--scale-total-offset)" : "0px",
          }}
        >
          <div
            className="flex-1 w-full max-w-[1200px] mx-auto flex flex-col items-center justify-end relative mt-2 z-10 pointer-events-none transform-gpu transition-transform duration-[800ms] ease-[cubic-bezier(0.2,0.8,0.2,1)]"
            style={{
              transform: isOpen ? "translateX(calc(-1 * var(--results-panel-shift)))" : "translateX(0px)",
            }}
          >
            {playableVideoUri ? (
              <div className="relative flex w-full items-end justify-center">
                <div className="relative flex h-[min(84vh,920px)] w-full max-w-[82vw] items-end justify-center">
                  <SeamlessVideoPlayer
                    ref={playerRef}
                    currentClip={currentClip}
                    preloadClip={preloadClip}
                    transitionDurationMs={0}
                    className="h-full w-full"
                    layerClassName="flex items-end justify-center"
                    videoClassName="h-full w-auto max-w-full object-contain [background:transparent] drop-shadow-[0_28px_60px_rgba(15,23,42,0.28)] -translate-y-10 md:-translate-y-16 scale-[1.08] md:scale-[1.15]"
                    onClipReady={(clip) => {
                      markReadyClip(clip.clipKey);
                      setVideoError("");
                    }}
                    onDisplayedClipChange={(clip) => {
                      markDisplayedClip(clip?.clipKey ?? null);
                    }}
                    onEnded={() => {
                      void handleVideoEnded();
                    }}
                    onPlaybackBlocked={() => {
                      setPlaybackBlocked(true);
                      pushToast("浏览器阻止了自动播放，请点击数字人区域中央的播放按钮继续。", "warning");
                    }}
                    onPlaybackStarted={() => {
                      setPlaybackBlocked(false);
                      setVideoError("");
                    }}
                    onTimeUpdate={handleVideoTimeUpdate}
                    onVideoError={handleVideoError}
                  />
                </div>
                {playbackBlocked ? (
                  <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-auto">
                    <button
                      onClick={handlePlayCurrentVideo}
                      className="inline-flex items-center gap-3 rounded-full border border-white/20 bg-white/12 px-5 py-3 text-sm font-medium text-white shadow-lg transition hover:bg-white/18"
                    >
                      <PlayCircle className="h-5 w-5" />
                      点击播放当前量表视频
                    </button>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="pointer-events-auto mb-28 flex min-h-[48vh] w-full max-w-[820px] flex-col items-center justify-center gap-4 rounded-[2rem] border border-white/12 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.18),transparent_38%),linear-gradient(135deg,rgba(15,23,42,0.68),rgba(15,23,42,0.42))] px-8 text-center text-white backdrop-blur-md">
                <div className="flex h-20 w-20 items-center justify-center rounded-full border border-white/15 bg-white/8">
                  <VideoOff className="h-8 w-8 text-sky-100/80" />
                </div>
                <div className="space-y-2">
                  <p className="text-xl font-medium">
                    {missingVideoFallback.isMissingVideo ? missingVideoFallback.title : "当前题目的数字人视频尚未接入"}
                  </p>
                  <p className="max-w-2xl text-sm leading-7 text-slate-200/80">
                    {missingVideoFallback.isMissingVideo
                      ? missingVideoFallback.description
                      : "请通过左侧量表区域点击选项作答，或等待视频资源就绪。"}
                  </p>
                </div>
              </div>
            )}
          </div>

          <div
            className="absolute bottom-4 md:bottom-5 inset-x-0 z-20 flex flex-col items-center w-full gap-[10px] pb-0 pointer-events-auto shadow-sm transform-gpu transition-transform duration-[800ms] ease-[cubic-bezier(0.2,0.8,0.2,1)]"
            style={{
              transform: isOpen ? "translateX(calc(-1 * var(--results-panel-shift)))" : "translateX(0px)",
            }}
          >
            {stageSummaryText ? (
              <div className="pointer-events-none rounded-full border border-white/18 bg-slate-950/28 px-4 py-2 text-xs text-white/90 shadow-[0_10px_30px_rgba(15,23,42,0.24)] backdrop-blur-md">
                {stageSummaryText}
              </div>
            ) : null}
            {responseWindowStatusText ? (
              <div className="pointer-events-none rounded-full border border-white/18 bg-slate-950/28 px-4 py-2 text-xs text-white/90 shadow-[0_10px_30px_rgba(15,23,42,0.24)] backdrop-blur-md">
                {responseWindowStatusText}
              </div>
            ) : null}
            <FloatingControlBar
              isRecording={isRecording}
              onToggleRecord={handleToggleRecord}
              onEnd={handleEnd}
              recordDisabled={!videoFinished || isSubmittingAnswer || isAdvancingAfterConfirmation || state.loading}
              endDisabled={isRecording || isSubmittingAnswer || isAdvancingAfterConfirmation}
              recordLabel={isRecording ? `结束录音 ${formatDuration(recordingElapsedMs)}` : "开始录音"}
            />
          </div>

        </div>

        {/* Subtitle — outside flex-1 so NOT affected by marginLeft/Right shift */}
        <div className="absolute left-[5%] lg:left-[10%] top-1/2 -translate-y-[40%] z-[100] pointer-events-none w-[240px] sm:w-[280px] flex items-center justify-center">
          <DraggableMessagePanel title="量表字幕" lines={assistantLines} />
        </div>

        {/* Left side: Scale questionnaire panel toggle */}
        <button
          onClick={() => setIsScaleOpen((current) => !current)}
          className={cn(
            "absolute top-1/2 -translate-y-1/2 z-30 transition-all duration-[800ms] flex flex-col items-center justify-center gap-1 bg-white/70 backdrop-blur-xl shadow-[0_4px_20px_rgba(59,130,246,0.15)] hover:text-primary-600 pointer-events-auto",
            isScaleOpen
              ? "-translate-x-1/2 rounded-full w-8 h-16 border border-white/80"
              : "left-0 rounded-r-xl w-8 py-4 border border-l-0 border-white/80 pl-0.5 hover:translate-x-1",
          )}
          style={isScaleOpen ? { left: "var(--scale-total-offset)" } : undefined}
        >
          {isScaleOpen ? (
            <ChevronLeft className="w-5 h-5 text-slate-500" />
          ) : (
            <>
              <span className="text-[11px] font-bold tracking-widest px-0.5 text-slate-600 mb-1" style={{ writingMode: "vertical-rl" }}>
                量表答题
              </span>
              <ChevronRight className="w-5 h-5 text-slate-500" />
            </>
          )}
        </button>

        {/* Left side: Scale questionnaire panel */}
        <div
          className={cn(
            "absolute top-0 bottom-0 my-auto z-20 transition-all duration-[800ms] pointer-events-auto origin-left flex flex-col justify-center transform-gpu",
            isScaleOpen ? "opacity-100" : "opacity-0 pointer-events-none",
          )}
          style={{
            width: "var(--scale-panel-width)",
            height: "fit-content",
            maxHeight: "90vh",
            left: isScaleOpen ? "var(--scale-panel-left)" : "calc(-1 * var(--scale-panel-width) - 50px)",
            transform: isScaleOpen ? "rotateY(15deg)" : "rotateY(15deg) translateX(-20px)",
          }}
        >
          <div className="w-full bg-slate-900/10 backdrop-blur-md rounded-3xl border border-indigo-400/60 shadow-[0_0_30px_rgba(99,102,241,0.6),inset_0_0_20px_rgba(165,180,252,0.4)] overflow-hidden flex flex-col ring-1 ring-indigo-400/30 p-5 shrink-0 transform-gpu">
            <div className="flex flex-col gap-4">
              {currentStage && (
                <div className="max-h-[40vh] overflow-y-auto rounded-2xl border border-white/12 bg-white/5 p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[0.96rem] font-semibold tracking-[0.08em] text-white/88">
                      {currentStage.stageLabel || "量表"}
                    </span>
                    <span className="text-sm font-medium text-white/60">
                      {isCurrentVideoStageIntro ? "引导" : `${currentItem?.index || 1}/${currentStageQuestionCount}`}
                    </span>
                  </div>
                  <p
                    className={cn(
                      "text-white/92",
                      isCurrentVideoStageIntro ? "text-[1rem] leading-8" : "text-[1.22rem] font-semibold leading-10",
                    )}
                  >
                    {currentPromptText || "题目加载中..."}
                  </p>
                </div>
              )}

              {isCurrentVideoStageIntro ? (
                <div className="rounded-2xl border border-sky-300/20 bg-sky-400/8 px-4 py-3 text-sm leading-7 text-sky-50/88">
                  当前正在播放本阶段引导语，播放结束后会自动显示本题选项。
                </div>
              ) : (
              <div className="flex flex-col gap-3">
                {currentOptions.map((option: AssessmentOption, optionIndex: number) => {
                  const isActive = activeAcceptedScore === option.score;
                  const badgeStyle = OPTION_BADGE_STYLES[optionIndex] || OPTION_BADGE_STYLES[OPTION_BADGE_STYLES.length - 1];
                  return (
                    <button
                      key={option.label || optionIndex}
                      disabled={!canAnswerCurrentQuestion}
                      onClick={() => handleSubmitClickAnswer(option)}
                      className={cn(
                        "text-left w-full rounded-2xl border px-5 py-4 text-base transition-all",
                        isActive
                          ? "border-emerald-400/50 bg-emerald-500/15 text-white shadow-[0_0_20px_rgba(52,211,153,0.15)]"
                          : canAnswerCurrentQuestion
                            ? "border-white/12 bg-white/5 text-white/85 hover:border-white/25 hover:bg-white/10"
                            : "border-white/8 bg-white/3 text-white/40 cursor-not-allowed",
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <span className={cn(
                          "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-base font-bold tracking-[0.08em]",
                          isActive ? badgeStyle.active : badgeStyle.inactive,
                        )}>
                          {OPTION_LABELS[optionIndex] || String(optionIndex + 1)}
                        </span>
                        <div>
                          <span className="text-[1.08rem] font-semibold leading-8">
                            {option.label || "选项" + (optionIndex + 1)}
                          </span>
                          {option.score != null && (
                            <span className="ml-2 text-sm font-medium text-white/55">({option.score}分)</span>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
              )}

              {isAdvancingAfterConfirmation && activeAcceptedLabel && (
                <div className="flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
                  <CheckCircle className="h-4 w-4 text-emerald-300" />
                  已选择：「{activeAcceptedLabel}」
                </div>
              )}
            </div>
          </div>
        </div>

        <button
          onClick={() => setIsOpen((current) => !current)}
          className={cn(
            "absolute top-1/2 -translate-y-1/2 z-30 transition-all duration-[800ms] flex flex-col items-center justify-center gap-1 bg-white/70 backdrop-blur-xl shadow-[0_4px_20px_rgba(59,130,246,0.15)] hover:text-primary-600 pointer-events-auto",
            isOpen
              ? "translate-x-1/2 rounded-full w-8 h-16 border border-white/80"
              : "right-0 rounded-l-xl w-8 py-4 border border-r-0 border-white/80 pr-0.5 hover:-translate-x-1",
          )}
          style={isOpen ? { right: "min(45vw, 650px)" } : undefined}
        >
          {!isOpen ? (
            <>
              <span className="text-[11px] font-bold tracking-widest px-0.5 text-slate-600 mb-1" style={{ writingMode: "vertical-rl" }}>
                实时结果
              </span>
              <ChevronLeft className="w-5 h-5 text-slate-500" />
            </>
          ) : (
            <ChevronRight className="w-5 h-5 text-slate-500" />
          )}
        </button>

        <div
          className={cn(
            "absolute top-[2%] bottom-[2%] z-20 transition-all duration-[800ms] pointer-events-auto origin-right w-[45vw] max-w-[650px]",
            isOpen ? "right-0 opacity-100" : "-right-[600px] opacity-0",
          )}
          style={isOpen ? { transform: "rotateY(-15deg)" } : undefined}
        >
          <div className="absolute inset-0 w-full h-full">
            <div className="w-full h-full bg-slate-900/10 transition-all duration-500 backdrop-blur-md rounded-3xl border border-indigo-400/60 shadow-[0_0_40px_rgba(99,102,241,0.6),inset_0_0_20px_rgba(165,180,252,0.4)] overflow-hidden flex flex-col relative z-30 ring-1 ring-indigo-400/30">
              <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-indigo-500/5 to-transparent pointer-events-none"></div>
              <div className="w-full h-full flex flex-col overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent relative z-10">
                <div className="w-full h-full min-h-0">
                  {isOpen && synthesizedConsultation ? (
                    <ConsultationStatusPanel
                      consultation={synthesizedConsultation}
                      onRefresh={handleRefresh}
                      refreshing={state.loading}
                      isRecording={isRecording}
                      liveTransport={isLiveStreamActive ? "SSE" : "HTTP"}
                      cameraStream={cameraStream}
                      cameraReady={cameraReady}
                      cameraError={cameraError}
                      cameraStatusTitle={cameraFeedback.title}
                      cameraStatusTone={cameraFeedback.tone}
                      microphoneStatusText={microphoneStatusTitle}
                      transcriptPending={isRecording || isSubmittingAnswer}
                      className="h-full"
                    />
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className={`absolute transition-all duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)] z-40 ${isOpen ? "opacity-0 scale-95 pointer-events-none" : "opacity-100 scale-100"} right-4 md:right-8 top-4 md:top-6`}>
          <CameraPreview
            className="w-[25vw] min-w-[160px] max-w-[260px] aspect-[4/3] rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.4)] border border-white/20 ml-auto"
            videoRef={cameraVideoRef}
            stream={cameraStream}
            cameraReady={cameraReady}
            audioActive={isRecording}
            title={cameraFeedback.title}
            headlineText={cameraFeedback.title}
            detailText={cameraFeedback.detail}
            errorText={cameraError}
            statusTone={cameraFeedback.tone}
            audioStatusText={microphoneStatusTitle}
          />
        </div>
      </div>
    </ConsultationLayout>
  );
}
