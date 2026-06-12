import { startTransition, useEffect, useEffectEvent, useMemo, useRef, useState, type CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight, LoaderCircle, PlayCircle, VideoOff } from "lucide-react";

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
  type SeamlessVideoClip,
  type SeamlessVideoErrorEvent,
  type SeamlessVideoPlayerHandle,
  type SeamlessVideoTimeUpdateEvent,
} from "../components/video";
import { ConsultationLayout } from "../layouts";
import {
  buildConsultationCurrentVideoNode,
  createConsultationVideoNodeTransitionAdapter,
  resolveMissingVideoNodeFallback,
  useVideoNodeTransitionController,
} from "../features/video-node";
import { buildRecordingFilename, formatDuration, sleep } from "../lib/mediaCapture";
import { useMultimodalAudioSubmission } from "../lib/useMultimodalAudioSubmission";
import { useAudioRecording, type RecordingCompletedPayload } from "../lib/useAudioRecording";
import { useCamera } from "../lib/useCamera";
import { useJsonEventStream } from "../lib/useJsonEventStream";
import { useMultimodalSession } from "../lib/useMultimodalSession";
import { useTimedToast } from "../lib/useTimedToast";
import { useVisualCapture } from "../lib/useVisualCapture";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";
import {
  uploadMultimodalAudioTurn,
} from "../services/api/multimodal.api";
import { getConsultationMultimodalLiveStreamUrl } from "../services/api/consultation.api";
import { mergeConsultationMultimodalLive } from "../lib/multimodalLiveMerge";
import type {
  ConsultationMultimodalLive,
  ConsultationMultimodalLivePatch,
  ConsultationSubtitleHistoryEntry,
} from "../types";

const STAGE_LABELS = ["问候说明", "主诉采集", "症状筛查", "风险筛查"];
const LIVE_REFRESH_INTERVAL_MS = 1000;
const SYSTEM_VIDEO_AUTO_COMMIT_THRESHOLD_SECONDS = 0.9;

declare global {
  interface Window {
    webkitAudioContext?: typeof AudioContext;
  }
}

function formatSubtitleHistoryLine(entry: ConsultationSubtitleHistoryEntry) {
  const speakerLabel = entry.speaker === "doctor" ? "数字人" : "用户";
  return `${speakerLabel}：${entry.text.trim()}`;
}

type LocalRecordingSnapshot = {
  promptKey: string;
  durationMs: number;
  startedAt: string;
  completedAt: string;
  mimeType: string;
  sizeBytes: number;
  objectUrl: string;
};

export default function ConsultationPage() {
  const navigate = useNavigate();
  const { state, actions } = useConsultationAppContext();
  const consultation = state.consultation;

  const [isOpen, setIsOpen] = useState(false);
  const [isSubmittingResponse, setIsSubmittingResponse] = useState(false);
  const [playbackBlocked, setPlaybackBlocked] = useState(false);
  const [videoError, setVideoError] = useState("");
  const [answerWindowOpenedAt, setAnswerWindowOpenedAt] = useState<string | null>(null);
  const [lastRecording, setLastRecording] = useState<LocalRecordingSnapshot | null>(null);
  const { cameraReady, cameraStream, cameraError, cameraFeedback } = useCamera({ enabled: true });
  const [subtitleUserTranscript, setSubtitleUserTranscript] = useState<string | null>(null);
  const isUnmountingRef = useRef(false);
  const { toast, pushToast } = useTimedToast();
  const { submitRecordedAudio } = useMultimodalAudioSubmission();

  const playerRef = useRef<SeamlessVideoPlayerHandle | null>(null);
  const cameraVideoRef = useRef<HTMLVideoElement | null>(null);
  const lastRecordingUrlRef = useRef<string | null>(null);
  const answerWindowPromptKeyRef = useRef<string | null>(null);
  const liveRefreshInFlightRef = useRef(false);
  const livePatchBufferRef = useRef<ConsultationMultimodalLive | null>(null);
  const livePatchFlushTimerRef = useRef<number | null>(null);
  const consultationStatusRef = useRef<string | null>(consultation?.status ?? null);
  const currentQuestionItemRef = useRef(consultation?.current_question_item ?? null);

  const currentQuestionKey = consultation?.current_question_key ?? null;
  const currentTurnId = consultation?.current_turn_id ?? null;
  const {
    ensureSession: ensureMultimodalSession,
  } = useMultimodalSession({
    linkedSessionId: consultation?.multimodal_session_id ?? null,
    resolveSessionId: async () => {
      const refreshedConsultation = await actions.refreshConsultation();
      return refreshedConsultation?.multimodal_session_id || null;
    },
    missingSessionMessage: "当前问诊会话缺少多模态会话绑定，请刷新页面后重试。",
  });

  const handleAudioRecordingComplete = useEffectEvent(
    async (payload: RecordingCompletedPayload) => {
      const { blob, mimeType, startedAt, completedAt } = payload;

      const objectUrl = URL.createObjectURL(blob);
      if (lastRecordingUrlRef.current) {
        URL.revokeObjectURL(lastRecordingUrlRef.current);
      }
      lastRecordingUrlRef.current = objectUrl;
      setLastRecording({
        promptKey: currentQuestionKey || "current",
        durationMs: completedAt.getTime() - startedAt.getTime(),
        startedAt: startedAt.toISOString(),
        completedAt: completedAt.toISOString(),
        mimeType,
        sizeBytes: blob.size,
        objectUrl,
      });

      // Upload + transcribe + submit
      setIsSubmittingResponse(true);
      try {
        if (!consultation || !currentQuestionKey) {
          pushToast("当前题目缺少转写所需上下文，请刷新后重试。", "error");
          return;
        }
        const consultationTurnId = consultation.current_turn_id || null;
        if (!consultationTurnId) {
          throw new Error("当前回答窗口缺少 turn_id，请刷新后重试。");
        }
        const submittedAudio = await submitRecordedAudio({
          payload,
          context: {
            consultation,
            currentQuestionKey,
            consultationTurnId,
          },
          ensureSession: ensureMultimodalSession,
          emptyRecordingMessage: "本轮录音内容为空，浏览器没有采集到有效音频，请重新录音。",
          emptyTranscriptMessage: "未识别到有效语音，请靠近麦克风并完整说一句后重试。",
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
              flow_run_id: context.consultation.session_id,
              question_key: context.currentQuestionKey,
              stage_id:
                context.consultation.current_stage_id ||
                context.consultation.current_question_item?.stage_id ||
                "unknown",
              node_id:
                context.consultation.current_node_id ||
                context.consultation.current_question_item?.node_id ||
                "unknown",
              duration_ms: durationMs,
              response_started_at: startedAtIso,
              response_completed_at: completedAtIso,
              mime_type: resolvedMimeType,
              turn_id: context.consultationTurnId,
              audio_file: audioBlob,
              filename: buildRecordingFilename(context.currentQuestionKey, resolvedMimeType),
            }),
        });
        setSubtitleUserTranscript(submittedAudio.transcriptText);

        await actions.submitConsultationTurn({
          input_type: "speech",
          turn_id: consultationTurnId,
          raw_input: submittedAudio.transcriptText,
          audio_uri: submittedAudio.transcriptReadyAudioTurn.audio_uri,
          transcript_text: submittedAudio.transcriptText,
          transcript_source: "dolphin_final",
          response_started_at: submittedAudio.startedAtIso,
          response_completed_at: submittedAudio.completedAtIso,
        });
        await captureSupplementalFrame(consultationTurnId);
        if (submittedAudio.transcriptReadyAudioTurn.processing_status !== "completed") {
          void waitForCompletedAudioTurn(
            submittedAudio.sessionId,
            submittedAudio.uploadedAudioTurn.audio_turn_id,
          ).catch(() => {});
        }
        pushToast("转写成功", "success", { durationMs: 1800 });
      } catch (caught) {
        pushToast(
          caught instanceof Error ? caught.message : "语音提交失败，请重新录音。",
          "error",
        );
      } finally {
        setIsSubmittingResponse(false);
      }
    },
  );

  const {
    isRecording,
    recordingElapsedMs,
    microphoneFeedback,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useAudioRecording({
    onRecordingComplete: handleAudioRecordingComplete,
    onError: (msg: string) => pushToast(msg, "error"),
    isUnmountingRef,
  });

  const { captureNow: captureSupplementalFrame } = useVisualCapture<string | null>({
    enabled:
      cameraReady &&
      !!currentQuestionKey &&
      !!consultation &&
      ["waiting_user_input", "recording_response", "processing_response", "running"].includes(
        consultation.status,
      ),
    cameraStream,
    videoRef: cameraVideoRef,
    uploadFn: async ({ blob, sampleIndex, startedAt, endedAt, context }) => {
      const imageFile = new File([blob], `capture-${sampleIndex}.jpg`, {
        type: blob.type || "image/jpeg",
      });
      await actions.submitConsultationVisualCapture({
        question_key: currentQuestionKey!,
        turn_id: context ?? currentTurnId ?? null,
        sample_started_at: startedAt,
        sample_ended_at: endedAt,
        sample_index: sampleIndex,
        mime_type: imageFile.type || "image/jpeg",
        image_file: imageFile,
      });
    },
  });

  const consultationCurrentVideoNode = useMemo(
    () => buildConsultationCurrentVideoNode(consultation),
    [consultation],
  );
  const consultationTransitionAdapter = useMemo(
    () => createConsultationVideoNodeTransitionAdapter({ consultation, actions }),
    [actions, consultation],
  );
  const {
    state: videoTransitionState,
    currentClip,
    preloadClip,
    requestPreview,
    commitCurrentNode,
    markReadyClip,
    markDisplayedClip,
    handleClipLoadError,
  } = useVideoNodeTransitionController({
    adapter: consultationTransitionAdapter,
  });
  const currentVideoNode = videoTransitionState.currentNode ?? consultationCurrentVideoNode;
  const playableVideoUri = currentClip?.src ?? null;
  const currentVideoNodeRef = useRef(currentVideoNode);
  const currentClipKeyRef = useRef<string | null>(currentClip?.clipKey ?? null);
  const pendingCommitRef = useRef(videoTransitionState.pendingCommit);
  const missingVideoFallback = useMemo(
    () => resolveMissingVideoNodeFallback(currentVideoNode),
    [currentVideoNode],
  );
  const promptText = currentVideoNode?.displayText ?? "";
  const responseWindowStatusText = useMemo(() => {
    if (!currentVideoNode?.responseRequired) {
      return "";
    }
    if (isSubmittingResponse) {
      return "Dolphin 正在转写本轮语音。";
    }
    if (isRecording) {
      return `本地录音中 ${formatDuration(recordingElapsedMs)}，停止后进入 Dolphin 转写。`;
    }
    if (consultation?.status === "waiting_user_input") {
      return answerWindowOpenedAt ? "回答窗口已开启，可开始本轮语音回答。" : "当前题目已进入等待回答态。";
    }
    if (lastRecording && lastRecording.promptKey === currentQuestionKey) {
      return `已采集本轮录音 ${formatDuration(lastRecording.durationMs)}。`;
    }
    return "";
  }, [
    answerWindowOpenedAt,
    consultation?.status,
    currentVideoNode?.responseRequired,
    currentQuestionKey,
    isRecording,
    isSubmittingResponse,
    lastRecording,
    recordingElapsedMs,
  ]);
  const subtitleUserLine = useMemo(() => {
    if (!currentVideoNode?.responseRequired) {
      return null;
    }
    if (subtitleUserTranscript?.trim()) {
      return `用户：${subtitleUserTranscript.trim()}`;
    }
    if (isSubmittingResponse) {
      return "用户：（Dolphin 正在转写本轮语音）";
    }
    if (isRecording) {
      return `用户：（Dolphin 识别中 ${formatDuration(recordingElapsedMs)}）`;
    }
    if (consultation?.status === "waiting_user_input") {
      return "用户：（回答窗口已开启，可开始语音回答）";
    }
    return null;
  }, [
    consultation?.status,
    currentVideoNode?.responseRequired,
    isRecording,
    isSubmittingResponse,
    recordingElapsedMs,
    subtitleUserTranscript,
  ]);
  const subtitlePanelLines = useMemo(() => {
    if (!consultation) {
      return ["数字人：会话尚未加载。", "用户：（等待会话恢复）"];
    }

    const persistedEntries = [...(consultation.subtitle_history || [])].sort(
      (left, right) => left.sequence - right.sequence,
    );
    const lines = persistedEntries.map((entry) => formatSubtitleHistoryLine(entry));

    if (subtitleUserLine?.trim()) {
      const activeUserEntry = [...persistedEntries]
        .reverse()
        .find((entry) => entry.speaker === "user" && entry.prompt_key === currentQuestionKey);
      const persistedUserLine = activeUserEntry ? formatSubtitleHistoryLine(activeUserEntry) : null;
      if (persistedUserLine !== subtitleUserLine.trim()) {
        if (
          activeUserEntry &&
          activeUserEntry.status === "draft" &&
          persistedUserLine &&
          lines[lines.length - 1] === persistedUserLine
        ) {
          lines[lines.length - 1] = subtitleUserLine.trim();
        } else {
          lines.push(subtitleUserLine.trim());
        }
      }
    }

    if (lines.length > 0) {
      return lines;
    }

    if (promptText.trim()) {
      return [`数字人：${promptText.trim()}`];
    }

    return ["数字人：当前会话尚未产生字幕。"];
  }, [
    consultation?.session_id,
    consultation?.subtitle_history,
    currentQuestionKey,
    promptText,
    subtitleUserLine,
  ]);

  const currentStageOrder =
    currentVideoNode?.stageOrder ??
    consultation?.current_stage?.stage_order ??
    consultation?.current_question_item?.stage_order ??
    1;
  const canAutoCompleteSystemPrompt = Boolean(
    consultation?.status === "waiting_system_completion" && currentVideoNode?.transitionMode === "auto_commit",
  );
  const canEnterAssessment = consultation?.status === "handoff_ready";

  const pushStoreToast = useEffectEvent((message: string, tone: "success" | "warning" | "error") => {
    pushToast(message, tone);
    actions.resetFeedback();
  });

  const flushBufferedLiveSnapshot = useEffectEvent(() => {
    const buffered = livePatchBufferRef.current;
    if (!buffered) {
      return;
    }
    livePatchBufferRef.current = null;
    startTransition(() => {
      actions.applyConsultationMultimodalLive(buffered);
    });
  });

  const applyLiveSnapshot = useEffectEvent((live: ConsultationMultimodalLivePatch) => {
    livePatchBufferRef.current = mergeConsultationMultimodalLive(
      livePatchBufferRef.current,
      live,
    );
    if (livePatchFlushTimerRef.current !== null) {
      return;
    }
    livePatchFlushTimerRef.current = window.setTimeout(() => {
      livePatchFlushTimerRef.current = null;
      flushBufferedLiveSnapshot();
    }, 180);
  });

  const {
    isActive: isLiveStreamActive,
    activeRef: liveStreamActiveRef,
  } = useJsonEventStream<ConsultationMultimodalLivePatch>({
    url:
      consultation?.session_id && typeof window !== "undefined"
        ? getConsultationMultimodalLiveStreamUrl(consultation.session_id)
        : null,
    onMessage: applyLiveSnapshot,
    enabled: isOpen,
  });

  const refreshLiveSnapshot = useEffectEvent(async () => {
    if (!consultation?.session_id || !isOpen) {
      return null;
    }
    if (typeof document !== "undefined" && document.visibilityState === "hidden") {
      return null;
    }
    if (liveRefreshInFlightRef.current) {
      return null;
    }
    if (liveStreamActiveRef.current) {
      return null;
    }

    liveRefreshInFlightRef.current = true;
    try {
      return await actions.refreshConsultationMultimodalLive();
    } finally {
      liveRefreshInFlightRef.current = false;
    }
  });

  useEffect(() => {
    consultationStatusRef.current = consultation?.status ?? null;
    currentQuestionItemRef.current = consultation?.current_question_item ?? null;
  }, [consultation?.status, consultation?.current_question_item]);

  useEffect(() => {
    currentVideoNodeRef.current = currentVideoNode;
  }, [currentVideoNode]);

  useEffect(() => {
    currentClipKeyRef.current = currentClip?.clipKey ?? null;
  }, [currentClip?.clipKey]);

  useEffect(() => {
    pendingCommitRef.current = videoTransitionState.pendingCommit;
  }, [videoTransitionState.pendingCommit]);

  useEffect(() => {
    const activeNode = videoTransitionState.currentNode;
    if (
      consultation?.status !== "waiting_system_completion" ||
      !activeNode?.questionKey ||
      activeNode.transitionMode !== "auto_commit"
    ) {
      return;
    }

    void requestPreview();
  }, [
    consultation?.status,
    videoTransitionState.currentNode?.nodeKey,
    videoTransitionState.currentNode?.questionKey,
    videoTransitionState.currentNode?.transitionMode,
  ]);

  useEffect(() => {
    if (state.message) {
      pushStoreToast(state.message, "success");
    }
  }, [state.message]);

  useEffect(() => {
    if (state.error) {
      pushStoreToast(state.error, "error");
    }
  }, [state.error]);

  useEffect(() => {
    if (videoError) {
      pushToast(videoError, "error");
    }
  }, [videoError]);

  useEffect(() => {
    if (videoTransitionState.previewError) {
      pushToast(`下一题视频预热失败，结束后会直接走正式推进。${videoTransitionState.previewError}`, "warning");
    }
  }, [pushToast, videoTransitionState.previewError]);

  useEffect(() => {
    if (videoTransitionState.transitionReason === "commit_mismatch") {
      pushToast("预热结果与正式推进结果不一致，已按正式结果重新切换。", "warning");
    }
  }, [pushToast, videoTransitionState.transitionReason]);

  useEffect(() => {
    if (cameraError) {
      pushToast(cameraError, "warning");
    }
  }, [cameraError, pushToast]);

  useEffect(() => {
    if (consultation?.status === "waiting_user_input" && currentQuestionKey) {
      if (answerWindowPromptKeyRef.current !== currentQuestionKey) {
        answerWindowPromptKeyRef.current = currentQuestionKey;
        setAnswerWindowOpenedAt(new Date().toISOString());
      }
      return;
    }

    if (!isRecording) {
      answerWindowPromptKeyRef.current = currentQuestionKey;
      setAnswerWindowOpenedAt(null);
    }
  }, [consultation?.status, currentQuestionKey, consultation?.current_turn_id, isRecording]);

  useEffect(() => {
    setSubtitleUserTranscript(null);
  }, [currentQuestionKey]);

  useEffect(() => {
    if (!consultation || !isOpen) {
      return;
    }

    void refreshLiveSnapshot();
    if (isLiveStreamActive) {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshLiveSnapshot();
    }, LIVE_REFRESH_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [consultation?.session_id, isLiveStreamActive, isOpen]);

  useEffect(() => {
    return () => {
      isUnmountingRef.current = true;
      if (livePatchFlushTimerRef.current !== null) {
        window.clearTimeout(livePatchFlushTimerRef.current);
      }
      if (lastRecordingUrlRef.current) {
        URL.revokeObjectURL(lastRecordingUrlRef.current);
      }
    };
  }, []);

  useEffect(() => {
    setPlaybackBlocked(false);
    setVideoError("");
  }, [currentClip?.clipKey]);

  async function handlePlayCurrentVideo() {
    const player = playerRef.current;
    if (!player) {
      return;
    }

    setPlaybackBlocked(false);
    setVideoError("");

    try {
      await player.playDisplayed();
    } catch {
      setPlaybackBlocked(true);
      pushToast("当前浏览器仍然阻止自动播放，需要手动点击播放按钮。", "warning");
    }
  }

  const handleVideoEnded = useEffectEvent(async (endedClip?: SeamlessVideoClip | null) => {
    const activeNode = currentVideoNodeRef.current;
    if (
      (endedClip?.clipKey && currentClipKeyRef.current && endedClip.clipKey !== currentClipKeyRef.current) ||
      !currentQuestionItemRef.current ||
      !activeNode?.questionKey ||
      consultationStatusRef.current !== "waiting_system_completion" ||
      activeNode.transitionMode !== "auto_commit" ||
      pendingCommitRef.current
    ) {
      return;
    }

    const updated = await commitCurrentNode();
    if (updated) {
      return;
    }

    const latestNode = currentVideoNodeRef.current;
    if (
      !latestNode?.questionKey ||
      consultationStatusRef.current !== "waiting_system_completion" ||
      latestNode.transitionMode !== "auto_commit"
    ) {
      return;
    }

    pushToast("当前系统视频已结束，但自动推进失败。请在右侧看板中点击刷新。", "warning");
  });

  async function handleMissingVideoContinue() {
    const updated = await commitCurrentNode();
    if (!updated) {
      pushToast("当前节点缺少视频资源，继续推进失败。请在右侧看板中点击刷新。", "warning");
    }
  }

  async function handleRefresh() {
    await actions.refreshConsultation();
    await refreshLiveSnapshot();
  }

  async function waitForCompletedAudioTurn(
    sessionId: string,
    audioTurnId: string,
  ) {
    const { getMultimodalAudioTurn } = await import("../services/api/multimodal.api");
    for (let attempt = 0; attempt < 180; attempt += 1) {
      const audioTurn = await getMultimodalAudioTurn(sessionId, audioTurnId);
      if (audioTurn.processing_status === "completed" || audioTurn.processing_status === "failed") {
        return audioTurn;
      }
      await sleep(500);
    }

    return null;
  }

  async function handleToggleRecord() {
    if (!consultation) {
      return;
    }

    if (isSubmittingResponse || state.loading) {
      return;
    }

    if (isRecording) {
      stopRecording();
      return;
    }

    if (consultation.status !== "waiting_user_input") {
      pushToast("当前还未进入回答窗口，需要先完成本轮问题视频播放。", "warning");
      return;
    }

    await startRecording();
  }

  async function handleEnd() {
    if (!consultation) {
      return;
    }

    if (!canEnterAssessment) {
      pushToast(
        consultation.status === "paused_for_human_review"
          ? "当前问诊正在等待人工复核，暂时不能进入量表评估。"
          : "当前问诊尚未完成，暂时不能进入量表评估。",
        "warning",
      );
      return;
    }

    const createdAssessment = await actions.handleStartAssessment();
    if (!createdAssessment) {
      pushToast("量表会话创建失败，请稍后重试。", "warning");
      return;
    }
    navigate(APP_PATHS.assessment, { state: { sessionId: createdAssessment.session_id } });
  }

  function handleVideoTimeUpdate(event: SeamlessVideoTimeUpdateEvent) {
    const activeNode = videoTransitionState.currentNode;
    if (
      !activeNode?.questionKey ||
      consultation?.status !== "waiting_system_completion" ||
      activeNode.transitionMode !== "auto_commit" ||
      videoTransitionState.pendingCommit
    ) {
      return;
    }

    const remainingSeconds = event.video.duration - event.video.currentTime;
    if (
      !Number.isFinite(remainingSeconds) ||
      remainingSeconds > SYSTEM_VIDEO_AUTO_COMMIT_THRESHOLD_SECONDS
    ) {
      return;
    }

    if (!videoTransitionState.pendingPreview) {
      void requestPreview();
    }
    void commitCurrentNode();
  }

  function handleVideoError(event: SeamlessVideoErrorEvent) {
    const clipKey = event.clip?.clipKey ?? null;
    const scope = handleClipLoadError(clipKey);
    if (scope === "prefetched") {
      pushToast("后台预热视频加载失败，结束后会按正式结果重新加载下一题。", "warning");
      return;
    }

    setVideoError("当前视频资源加载失败，请稍后重试。");
    setPlaybackBlocked(false);
  }

  if (!consultation) {
    return (
      <ConsultationLayout backgroundImage="/4K.png" title="智能评估">
        <div className="flex h-full w-full items-center justify-center px-6">
          <div className="w-full max-w-xl rounded-[2rem] border border-white/20 bg-slate-950/35 px-8 py-10 text-center text-white shadow-[0_25px_80px_rgba(15,23,42,0.28)] backdrop-blur-xl">
            <LoaderCircle className="mx-auto mb-4 h-8 w-8 animate-spin text-sky-200" />
            <p className="text-lg font-medium">{state.loading ? "正在恢复问诊会话..." : "当前没有可继续的问诊会话。"}</p>
            <p className="mt-3 text-sm text-slate-200/75">请从首页或问诊准备页重新进入主流程。</p>
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

  if (consultation.status === "handoff_ready" || consultation.status === "paused_for_human_review") {
    return (
      <ConsultationLayout backgroundImage="/4K.png" title="智能评估">
        <div className="absolute inset-x-0 top-0 z-50 pointer-events-none">
          <div className="pointer-events-auto">
            <ConsultationProgress currentStageOrder={STAGE_LABELS.length} steps={STAGE_LABELS} />
          </div>
        </div>
        <FlowCompletionState
          title={consultation.status === "paused_for_human_review" ? "问诊等待人工复核" : "问诊流程已完成"}
          description={
            consultation.status === "paused_for_human_review"
              ? "当前问诊需要人工复核，请等待进一步处理。"
              : "请点击下方按钮进入量表评估阶段。"
          }
          actionLabel={consultation.status === "handoff_ready" ? "进入量表评估" : undefined}
          onAction={consultation.status === "handoff_ready" ? handleEnd : undefined}
        />
      </ConsultationLayout>
    );
  }

  return (
    <ConsultationLayout backgroundImage="/4K.png" title="智能评估">
      <div className="absolute inset-x-0 top-0 z-50 pointer-events-none">
        <div className="pointer-events-auto">
          <ConsultationProgress currentStageOrder={currentStageOrder} steps={STAGE_LABELS} />
        </div>
      </div>

      <AppToast toast={toast} />

      <div
        style={
          {
            "--results-panel-reserve": "min(45vw, 650px)",
            "--results-panel-shift": "calc(var(--results-panel-reserve) / 2)",
          } as CSSProperties
        }
        className="flex w-full h-full relative z-10 bg-transparent pt-8 overflow-hidden [perspective:2000px]"
      >
        <div
          className="flex-1 relative h-full flex flex-col items-center transition-all duration-[800ms] min-h-0 perspective-[1200px]"
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
                    className="h-full w-full"
                    layerClassName="flex items-end justify-center"
                    videoClassName="h-full w-auto max-w-full object-contain [background:transparent] drop-shadow-[0_28px_60px_rgba(15,23,42,0.28)] -translate-y-10 md:-translate-y-16 scale-[1.08] md:scale-[1.15]"
                    onClipReady={(clip) => {
                      markReadyClip(clip.clipKey);
                      setVideoError("");
                    }}
                    onDisplayedClipChange={(clip) => {
                      markDisplayedClip(clip?.clipKey ?? null);
                      const activeNode = videoTransitionState.currentNode;
                      const hasPrefetchedNextNode = Boolean(
                        videoTransitionState.prefetchedNode &&
                        videoTransitionState.prefetchedNode.nodeKey !== activeNode?.nodeKey,
                      );
                      if (
                        clip?.clipKey === currentClip?.clipKey &&
                        activeNode?.questionKey &&
                        consultation?.status === "waiting_system_completion" &&
                        activeNode.transitionMode === "auto_commit" &&
                        !videoTransitionState.pendingCommit &&
                        !videoTransitionState.pendingPreview &&
                        !hasPrefetchedNextNode
                      ) {
                        void requestPreview();
                      }
                    }}
                    onEnded={(clip) => {
                      void handleVideoEnded(clip);
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
                      点击播放当前问诊视频
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
                    {missingVideoFallback.isMissingVideo ? missingVideoFallback.title : "当前题目的视频资源尚未接入"}
                  </p>
                  <p className="max-w-2xl text-sm leading-7 text-slate-200/80">
                    {missingVideoFallback.isMissingVideo
                      ? missingVideoFallback.description
                      : "真实会话状态已经接通，但当前阶段的 manifest 仍未提供可播放视频 URI。"}
                  </p>
                </div>
                {missingVideoFallback.behavior === "manual_commit" && canAutoCompleteSystemPrompt ? (
                  <button
                    onClick={() => {
                      void handleMissingVideoContinue();
                    }}
                    className="pointer-events-auto rounded-full border border-white/20 bg-white/12 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-white/18"
                  >
                    {missingVideoFallback.actionLabel || "继续"}
                  </button>
                ) : null}
              </div>
            )}
          </div>

          <div
            className="absolute bottom-4 md:bottom-5 inset-x-0 z-20 flex flex-col items-center w-full gap-[10px] pb-0 pointer-events-auto shadow-sm transform-gpu transition-transform duration-[800ms] ease-[cubic-bezier(0.2,0.8,0.2,1)]"
            style={{
              transform: isOpen ? "translateX(calc(-1 * var(--results-panel-shift)))" : "translateX(0px)",
            }}
          >
            {responseWindowStatusText ? (
              <div className="pointer-events-none rounded-full border border-white/18 bg-slate-950/28 px-4 py-2 text-xs text-white/90 shadow-[0_10px_30px_rgba(15,23,42,0.24)] backdrop-blur-md">
                {responseWindowStatusText}
              </div>
            ) : null}
            <FloatingControlBar
              isRecording={isRecording}
              onToggleRecord={handleToggleRecord}
              onEnd={handleEnd}
              recordDisabled={(!isRecording && consultation.status !== "waiting_user_input") || isSubmittingResponse || state.loading}
              endDisabled={isRecording || isSubmittingResponse || !canEnterAssessment}
              recordLabel={isRecording ? `结束录音 ${formatDuration(recordingElapsedMs)}` : "开始录音"}
              endLabel={canEnterAssessment ? "进入量表评估" : "完成问诊后进入量表"}
            />
          </div>

          <div className="absolute left-[5%] lg:left-[10%] top-1/2 -translate-y-[40%] z-[100] pointer-events-none w-[240px] sm:w-[280px] flex items-center justify-center">
            <DraggableMessagePanel title="字幕状态" lines={subtitlePanelLines} />
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
                  {isOpen ? (
                    <ConsultationStatusPanel
                      consultation={consultation}
                      onRefresh={handleRefresh}
                      refreshing={state.loading}
                      isRecording={isRecording}
                      liveTransport={isLiveStreamActive ? "SSE" : "HTTP"}
                      cameraStream={cameraStream}
                      cameraReady={cameraReady}
                      cameraError={cameraError}
                      cameraStatusTitle={cameraFeedback.title}
                      cameraStatusTone={cameraFeedback.tone}
                      microphoneStatusText={microphoneFeedback.title}
                      transcriptPending={isRecording || isSubmittingResponse}
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
            audioStatusText={microphoneFeedback.title}
          />
        </div>
      </div>
    </ConsultationLayout>
  );
}
