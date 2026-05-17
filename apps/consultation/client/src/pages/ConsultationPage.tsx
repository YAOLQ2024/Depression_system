import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight, LoaderCircle, PlayCircle, VideoOff } from "lucide-react";

import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { AppToast } from "../components/AppToast";
import { CameraPreview } from "../components/CameraPreview";
import { ConsultationProgress } from "../components/ConsultationProgress";
import { ConsultationStatusPanel } from "../components/ConsultationStatusPanel";
import { DraggableMessagePanel } from "../components/DraggableMessagePanel";
import { FloatingControlBar } from "../components/FloatingControlBar";
import { ConsultationLayout } from "../layouts";
import { useTimedToast } from "../lib/useTimedToast";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";
import type { ConsultationSession } from "../types";

const STAGE_LABELS = ["问候说明", "主诉采集", "现病史", "风险筛查"];
const RECORDING_MIME_CANDIDATES = ["audio/ogg;codecs=opus", "audio/ogg", "audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
const CAMERA_CAPTURE_INTERVAL_MS = 2500;

type BrowserSpeechRecognitionResult = {
  0: {
    transcript: string;
  };
  isFinal: boolean;
  length: number;
};

type BrowserSpeechRecognitionEvent = Event & {
  resultIndex: number;
  results: ArrayLike<BrowserSpeechRecognitionResult>;
};

type BrowserSpeechRecognitionErrorEvent = Event & {
  error?: string;
};

type BrowserSpeechRecognition = EventTarget & {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onend: ((event: Event) => void) | null;
  onerror: ((event: BrowserSpeechRecognitionErrorEvent) => void) | null;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

declare global {
  interface Window {
    SpeechRecognition?: BrowserSpeechRecognitionConstructor;
    webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor;
    webkitAudioContext?: typeof AudioContext;
  }
}

function resolvePlayableVideoUri(session: ConsultationSession | null) {
  const candidate = session?.current_prompt_video_uri ?? session?.current_question_item?.video_uri ?? "";
  const normalized = candidate.trim();

  if (!normalized || normalized.toUpperCase() === "TBD") {
    return null;
  }

  return normalized;
}

function resolvePromptText(session: ConsultationSession | null) {
  const questionText = session?.current_prompt_question_text?.trim() || session?.current_question_item?.question_text?.trim();
  if (questionText) {
    return questionText;
  }

  const stageLabel = session?.current_stage?.stage_label || session?.current_question_item?.stage_label;
  if (stageLabel) {
    return `当前处于“${stageLabel}”阶段，题目文案待加载。`;
  }

  return "当前题目内容待加载。";
}

function resolveSubtitleText(session: ConsultationSession | null) {
  const subtitleText = session?.current_prompt_subtitle_text?.trim() || session?.current_question_item?.subtitle_text?.trim();
  if (subtitleText) {
    return subtitleText;
  }

  return resolvePromptText(session);
}

function splitPromptSegments(text: string) {
  return text
    .replace(/[!?！？]/g, "。")
    .split("。")
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map((segment) => `${segment}。`);
}

function buildDialoguePanelMessage(
  session: ConsultationSession | null,
  promptText: string,
  subtitleText: string,
  patientLineOverride?: string | null,
) {
  if (!session) {
    return "数字人：会话尚未加载。\n患者：（等待会话恢复）";
  }

  const currentQuestion = session.current_question_item;
  if (!currentQuestion?.response_required) {
    const segments = splitPromptSegments(promptText);
    const firstLine = segments[0] || promptText;
    const secondLine = segments.slice(1).join("") || (subtitleText !== promptText ? subtitleText : "") || "接下来，我们正式开始吧。";
    return `数字人：${firstLine}\n数字人：${secondLine}`;
  }

  let patientLine = patientLineOverride || "患者：（等待本轮患者回答）";
  if (!patientLineOverride && session.status === "recording_response") {
    patientLine = "患者：（正在录音）";
  } else if (!patientLineOverride && session.status === "processing_response") {
    patientLine = "患者：（本轮回答处理中）";
  } else if (!patientLineOverride && session.status !== "waiting_user_input") {
    patientLine = "患者：（当前阶段尚未进入回答窗口）";
  }

  return `数字人：${promptText}\n${patientLine}`;
}

function pickSupportedRecordingMimeType() {
  if (typeof MediaRecorder === "undefined" || typeof MediaRecorder.isTypeSupported !== "function") {
    return "";
  }

  return RECORDING_MIME_CANDIDATES.find((candidate) => MediaRecorder.isTypeSupported(candidate)) || "";
}

function getSpeechRecognitionConstructor() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function mapMimeTypeToAudioFormat(mimeType: string) {
  const normalized = mimeType.toLowerCase();
  if (normalized.includes("wav")) {
    return "wav";
  }
  if (normalized.includes("ogg")) {
    return "ogg";
  }
  if (normalized.includes("flac")) {
    return "flac";
  }
  return null;
}

async function blobToBase64(blob: Blob) {
  const arrayBuffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(arrayBuffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return window.btoa(binary);
}

function encodeWav(audioBuffer: AudioBuffer) {
  const channelCount = Math.min(audioBuffer.numberOfChannels, 1);
  const sampleRate = audioBuffer.sampleRate;
  const samples = audioBuffer.length;
  const bytesPerSample = 2;
  const dataSize = samples * channelCount * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);
  let offset = 0;

  function writeString(value: string) {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset, value.charCodeAt(index));
      offset += 1;
    }
  }

  writeString("RIFF");
  view.setUint32(offset, 36 + dataSize, true);
  offset += 4;
  writeString("WAVE");
  writeString("fmt ");
  view.setUint32(offset, 16, true);
  offset += 4;
  view.setUint16(offset, 1, true);
  offset += 2;
  view.setUint16(offset, channelCount, true);
  offset += 2;
  view.setUint32(offset, sampleRate, true);
  offset += 4;
  view.setUint32(offset, sampleRate * channelCount * bytesPerSample, true);
  offset += 4;
  view.setUint16(offset, channelCount * bytesPerSample, true);
  offset += 2;
  view.setUint16(offset, 16, true);
  offset += 2;
  writeString("data");
  view.setUint32(offset, dataSize, true);
  offset += 4;

  const channelData = audioBuffer.getChannelData(0);
  for (let index = 0; index < samples; index += 1) {
    const sample = Math.max(-1, Math.min(1, channelData[index] || 0));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += 2;
  }

  return buffer;
}

async function convertRecordedBlobToUpload(blob: Blob, mimeType: string) {
  const AudioContextCtor = window.AudioContext || window.webkitAudioContext;

  if (AudioContextCtor) {
    try {
      const context = new AudioContextCtor();
      const decoded = await context.decodeAudioData(await blob.arrayBuffer());
      const wavBuffer = encodeWav(decoded);
      await context.close();
      return {
        audioBase64: await blobToBase64(new Blob([wavBuffer], { type: "audio/wav" })),
        audioFormat: "wav",
        samplingRate: decoded.sampleRate,
      };
    } catch {
      // fall back below
    }
  }

  const directFormat = mapMimeTypeToAudioFormat(mimeType);
  if (!directFormat) {
    throw new Error("当前浏览器录音格式无法直接提交，建议使用 Chrome 并允许 OGG/Opus 或 WAV 转换。");
  }

  return {
    audioBase64: await blobToBase64(blob),
    audioFormat: directFormat,
    samplingRate: null,
  };
}

async function captureVideoFrame(videoElement: HTMLVideoElement, mimeType = "image/jpeg") {
  if (!videoElement.videoWidth || !videoElement.videoHeight) {
    return null;
  }
  const canvas = document.createElement("canvas");
  canvas.width = videoElement.videoWidth;
  canvas.height = videoElement.videoHeight;
  const context = canvas.getContext("2d");
  if (!context) {
    return null;
  }
  context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
  return new Promise<Blob | null>((resolve) => {
    canvas.toBlob((blob) => resolve(blob), mimeType, 0.85);
  });
}

function formatDuration(durationMs: number) {
  const totalSeconds = Math.max(0, Math.floor(durationMs / 1000));
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
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
  const [isRecording, setIsRecording] = useState(false);
  const [isSubmittingResponse, setIsSubmittingResponse] = useState(false);
  const [playbackBlocked, setPlaybackBlocked] = useState(false);
  const [videoError, setVideoError] = useState("");
  const [isCompletingSystemQuestion, setIsCompletingSystemQuestion] = useState(false);
  const [recordingElapsedMs, setRecordingElapsedMs] = useState(0);
  const [answerWindowOpenedAt, setAnswerWindowOpenedAt] = useState<string | null>(null);
  const [lastRecording, setLastRecording] = useState<LocalRecordingSnapshot | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [speechTranscript, setSpeechTranscript] = useState("");
  const [recognitionInterimTranscript, setRecognitionInterimTranscript] = useState("");
  const { toast, pushToast } = useTimedToast();

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const cameraVideoRef = useRef<HTMLVideoElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const speechRecognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingStartedAtRef = useRef<Date | null>(null);
  const answerWindowPromptKeyRef = useRef<string | null>(null);
  const lastRecordingUrlRef = useRef<string | null>(null);
  const isUnmountingRef = useRef(false);
  const frameIndexRef = useRef(0);
  const captureInFlightRef = useRef(false);
  const speechTranscriptRef = useRef("");
  const recognitionInterimRef = useRef("");

  const playableVideoUri = useMemo(() => resolvePlayableVideoUri(consultation), [consultation]);
  const promptText = useMemo(() => resolvePromptText(consultation), [consultation]);
  const subtitleText = useMemo(() => resolveSubtitleText(consultation), [consultation]);
  const liveTranscriptText = useMemo(
    () => `${speechTranscript}${recognitionInterimTranscript}`.trim(),
    [recognitionInterimTranscript, speechTranscript],
  );
  const currentPromptKey = consultation?.current_question_item?.question_key ?? consultation?.current_prompt_key ?? null;
  const responseWindowStatusText = useMemo(() => {
    if (!consultation?.current_question_item?.response_required) {
      return "";
    }
    if (isSubmittingResponse) {
      return "本轮录音已结束，正在提交回答窗口。";
    }
    if (isRecording) {
      return `本地录音中 ${formatDuration(recordingElapsedMs)}`;
    }
    if (consultation.status === "waiting_user_input") {
      return answerWindowOpenedAt ? "回答窗口已开启，可开始本轮语音回答。" : "当前题目已进入等待回答态。";
    }
    if (lastRecording && lastRecording.promptKey === currentPromptKey) {
      return `已采集本轮录音 ${formatDuration(lastRecording.durationMs)}。`;
    }
    return "";
  }, [
    answerWindowOpenedAt,
    consultation?.current_question_item?.response_required,
    consultation?.status,
    currentPromptKey,
    isRecording,
    isSubmittingResponse,
    lastRecording,
    recordingElapsedMs,
  ]);
  const patientLineOverride = useMemo(() => {
    if (!consultation?.current_question_item?.response_required) {
      return null;
    }
    if (isSubmittingResponse) {
      return "患者：（本轮录音已结束，正在提交回答窗口）";
    }
    if (isRecording) {
      return `患者：（正在录音 ${formatDuration(recordingElapsedMs)}）`;
    }
    if (consultation.status === "waiting_user_input") {
      return "患者：（回答窗口已开启，可开始语音回答）";
    }
    return null;
  }, [consultation?.current_question_item?.response_required, consultation?.status, isRecording, isSubmittingResponse, recordingElapsedMs]);
  const dialoguePanelMessage = useMemo(
    () => buildDialoguePanelMessage(consultation, promptText, subtitleText, patientLineOverride),
    [consultation, patientLineOverride, promptText, subtitleText],
  );

  const currentStageOrder = consultation?.current_stage?.stage_order ?? consultation?.current_question_item?.stage_order ?? 1;
  const currentStageLabel =
    consultation?.current_stage?.stage_label ||
    consultation?.current_question_item?.stage_label ||
    STAGE_LABELS[Math.max(0, Math.min(STAGE_LABELS.length - 1, currentStageOrder - 1))];
  const canAutoCompleteSystemPrompt = Boolean(
    consultation?.status === "waiting_system_completion" &&
      consultation.current_question_item &&
      consultation.current_question_item.response_required === false,
  );

  useEffect(() => {
    if (state.message) {
      pushToast(state.message, "success");
      actions.resetFeedback();
    }
  }, [actions, pushToast, state.message]);

  useEffect(() => {
    if (state.error) {
      pushToast(state.error, "error");
      actions.resetFeedback();
    }
  }, [actions, pushToast, state.error]);

  useEffect(() => {
    if (videoError) {
      pushToast(videoError, "error");
    }
  }, [videoError]);

  useEffect(() => {
    if (cameraError) {
      pushToast(cameraError, "warning");
    }
  }, [cameraError, pushToast]);

  useEffect(() => {
    if (consultation?.status === "waiting_user_input" && currentPromptKey) {
      if (answerWindowPromptKeyRef.current !== currentPromptKey) {
        answerWindowPromptKeyRef.current = currentPromptKey;
        setAnswerWindowOpenedAt(new Date().toISOString());
        setRecordingElapsedMs(0);
      }
      return;
    }

    if (!isRecording) {
      answerWindowPromptKeyRef.current = currentPromptKey;
      setAnswerWindowOpenedAt(null);
      setRecordingElapsedMs(0);
    }
  }, [consultation?.status, currentPromptKey, isRecording]);

  useEffect(() => {
    speechTranscriptRef.current = speechTranscript;
  }, [speechTranscript]);

  useEffect(() => {
    recognitionInterimRef.current = recognitionInterimTranscript;
  }, [recognitionInterimTranscript]);

  useEffect(() => {
    if (!isRecording) {
      return;
    }

    const timer = window.setInterval(() => {
      if (!recordingStartedAtRef.current) {
        return;
      }
      setRecordingElapsedMs(Date.now() - recordingStartedAtRef.current.getTime());
    }, 250);

    return () => window.clearInterval(timer);
  }, [isRecording]);

  useEffect(() => {
    if (!consultation) {
      return;
    }

    void actions.refreshConsultationMultimodalLive();
    const timer = window.setInterval(() => {
      void actions.refreshConsultationMultimodalLive();
    }, 2000);

    return () => window.clearInterval(timer);
  }, [actions, consultation?.session_id]);

  useEffect(() => {
    if (!consultation?.current_question_item?.question_key || !cameraReady) {
      return;
    }
    if (!["waiting_user_input", "recording_response", "processing_response", "running"].includes(consultation.status)) {
      return;
    }

    void submitCameraCaptures();
    const timer = window.setInterval(() => {
      void submitCameraCaptures();
    }, CAMERA_CAPTURE_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [cameraReady, consultation?.current_question_item?.question_key, consultation?.status]);

  useEffect(() => {
    return () => {
      isUnmountingRef.current = true;
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
      speechRecognitionRef.current?.abort();
      if (lastRecordingUrlRef.current) {
        URL.revokeObjectURL(lastRecordingUrlRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setCameraError("当前浏览器不支持摄像头采集。");
      return;
    }

    let cancelled = false;

    async function setupCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "user",
            width: { ideal: 960 },
            height: { ideal: 720 },
          },
        });
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        cameraStreamRef.current = stream;
        setCameraStream(stream);
        setCameraReady(true);
        setCameraError("");
      } catch (caught) {
        if (!cancelled) {
          setCameraReady(false);
          setCameraStream(null);
          setCameraError(caught instanceof Error ? caught.message : "摄像头授权失败。");
        }
      }
    }

    void setupCamera();

    return () => {
      cancelled = true;
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
      cameraStreamRef.current = null;
      setCameraStream(null);
      setCameraReady(false);
    };
  }, []);

  useEffect(() => {
    setPlaybackBlocked(false);
    setVideoError("");

    if (!playableVideoUri) {
      return;
    }

    const videoElement = videoRef.current;
    if (!videoElement) {
      return;
    }

    const playPromise = videoElement.play();
    if (playPromise) {
      void playPromise
        .then(() => setPlaybackBlocked(false))
        .catch(() => {
          setPlaybackBlocked(true);
          pushToast("浏览器阻止了自动播放，请点击数字人区域中央的播放按钮继续。", "warning");
        });
    }
  }, [consultation?.current_prompt_key, playableVideoUri]);

  async function handlePlayCurrentVideo() {
    const videoElement = videoRef.current;
    if (!videoElement) {
      return;
    }

    setPlaybackBlocked(false);
    setVideoError("");

    try {
      await videoElement.play();
    } catch {
      setPlaybackBlocked(true);
      pushToast("当前浏览器仍然阻止自动播放，需要手动点击播放按钮。", "warning");
    }
  }

  async function handleVideoEnded() {
    if (!consultation?.current_question_item || !canAutoCompleteSystemPrompt || isCompletingSystemQuestion) {
      return;
    }

    setIsCompletingSystemQuestion(true);

    try {
      const updated = await actions.completeConsultationSystemQuestionItem(consultation.current_question_item.question_key);
      if (!updated) {
        pushToast("问候视频已结束，但自动推进失败。请在右侧看板中点击刷新。", "warning");
      }
    } finally {
      setIsCompletingSystemQuestion(false);
    }
  }

  async function handleRefresh() {
    await actions.refreshConsultation();
    await actions.refreshConsultationMultimodalLive();
  }

  function cleanupRecorderResources() {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    mediaRecorderRef.current = null;
    audioChunksRef.current = [];
  }

  function stopSpeechRecognition() {
    const recognition = speechRecognitionRef.current;
    if (!recognition) {
      return;
    }
    recognition.onresult = null;
    recognition.onerror = null;
    recognition.onend = null;
    try {
      recognition.stop();
    } catch {
      recognition.abort();
    }
    speechRecognitionRef.current = null;
  }

  function startSpeechRecognition() {
    const SpeechRecognitionCtor = getSpeechRecognitionConstructor();
    if (!SpeechRecognitionCtor) {
      pushToast("当前浏览器不支持内置语音转写，文本模态可能无法同步出结果。", "warning");
      return;
    }

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = "zh-CN";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      let finalText = "";
      let interimText = "";
      for (let index = 0; index < event.results.length; index += 1) {
        const result = event.results[index];
        const transcript = result[0]?.transcript?.trim() || "";
        if (!transcript) {
          continue;
        }
        if (result.isFinal) {
          finalText += transcript;
        } else {
          interimText += transcript;
        }
      }
      speechTranscriptRef.current = finalText;
      recognitionInterimRef.current = interimText;
      setSpeechTranscript(finalText);
      setRecognitionInterimTranscript(interimText);
    };
    recognition.onerror = (event) => {
      if (event.error && event.error !== "no-speech" && event.error !== "aborted") {
        pushToast(`浏览器语音识别不可用：${event.error}`, "warning");
      }
    };
    recognition.onend = () => {
      speechRecognitionRef.current = null;
    };
    speechRecognitionRef.current = recognition;
    recognition.start();
  }

  async function submitCameraCaptures(turnId?: string | null) {
    if (!consultation?.current_question_item?.question_key || !cameraVideoRef.current || captureInFlightRef.current) {
      return;
    }
    if (!cameraReady) {
      return;
    }

    captureInFlightRef.current = true;
    const startedAt = new Date().toISOString();

    try {
      const blob = await captureVideoFrame(cameraVideoRef.current);
      if (!blob) {
        return;
      }

      frameIndexRef.current += 1;
      const frameIndex = frameIndexRef.current;
      const endedAt = new Date().toISOString();
      const imageFile = new File([blob], `capture-${frameIndex}.jpg`, { type: blob.type || "image/jpeg" });
      const payload = {
        question_key: consultation.current_question_item.question_key,
        turn_id: turnId || null,
        capture_started_at: startedAt,
        capture_ended_at: endedAt,
        frame_index: frameIndex,
        mime_type: imageFile.type || "image/jpeg",
        image_file: imageFile,
      };

      await Promise.all([
        actions.submitConsultationFaceCapture(payload),
        actions.submitConsultationPoseCapture(payload),
      ]);
    } finally {
      captureInFlightRef.current = false;
    }
  }

  async function startBrowserRecording() {
    if (typeof window === "undefined" || typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      pushToast("当前浏览器不支持麦克风录音。", "error");
      return;
    }

    if (typeof MediaRecorder === "undefined") {
      pushToast("当前浏览器不支持 MediaRecorder，无法执行本地录音。", "error");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = pickSupportedRecordingMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      const startedAt = new Date();

      if (lastRecordingUrlRef.current) {
        URL.revokeObjectURL(lastRecordingUrlRef.current);
        lastRecordingUrlRef.current = null;
      }
      setLastRecording(null);
      audioChunksRef.current = [];
      mediaStreamRef.current = stream;
      mediaRecorderRef.current = recorder;
      recordingStartedAtRef.current = startedAt;
      speechTranscriptRef.current = "";
      recognitionInterimRef.current = "";
      setSpeechTranscript("");
      setRecognitionInterimTranscript("");
      setRecordingElapsedMs(0);
      setIsRecording(true);
      startSpeechRecognition();

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onerror = () => {
        cleanupRecorderResources();
        recordingStartedAtRef.current = null;
        setIsRecording(false);
        setRecordingElapsedMs(0);
        pushToast("浏览器录音过程中出现错误，请重试。", "error");
      };

      recorder.onstop = async () => {
        if (isUnmountingRef.current) {
          cleanupRecorderResources();
          recordingStartedAtRef.current = null;
          stopSpeechRecognition();
          return;
        }

        const completedAt = new Date();
        const responseStartedAt = recordingStartedAtRef.current || completedAt;
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const transcriptText = `${speechTranscriptRef.current}${recognitionInterimRef.current}`.trim() || null;
        const objectUrl = URL.createObjectURL(blob);

        if (lastRecordingUrlRef.current) {
          URL.revokeObjectURL(lastRecordingUrlRef.current);
        }
        lastRecordingUrlRef.current = objectUrl;
        setLastRecording({
          promptKey: currentPromptKey || "current",
          durationMs: completedAt.getTime() - responseStartedAt.getTime(),
          startedAt: responseStartedAt.toISOString(),
          completedAt: completedAt.toISOString(),
          mimeType: recorder.mimeType || "audio/webm",
          sizeBytes: blob.size,
          objectUrl,
        });
        cleanupRecorderResources();
        recordingStartedAtRef.current = null;
        setIsRecording(false);
        setRecordingElapsedMs(0);
        setIsSubmittingResponse(true);
        stopSpeechRecognition();

        try {
          const upload = await convertRecordedBlobToUpload(blob, recorder.mimeType || blob.type || "audio/webm");
          await actions.submitConsultationTurn({
            input_type: "speech",
            raw_input: transcriptText,
            transcript_text: transcriptText,
            audio_base64: upload.audioBase64,
            audio_format: upload.audioFormat,
            sampling_rate: upload.samplingRate,
            response_started_at: responseStartedAt.toISOString(),
            response_completed_at: completedAt.toISOString(),
          });
          await submitCameraCaptures();
        } finally {
          setIsSubmittingResponse(false);
        }
      };

      recorder.start();
    } catch (caught) {
      cleanupRecorderResources();
      recordingStartedAtRef.current = null;
      stopSpeechRecognition();
      setIsRecording(false);
      setRecordingElapsedMs(0);
      pushToast(caught instanceof Error ? caught.message : "麦克风授权失败，无法开始录音。", "error");
    }
  }

  function stopBrowserRecording() {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      cleanupRecorderResources();
      recordingStartedAtRef.current = null;
      stopSpeechRecognition();
      setIsRecording(false);
      setRecordingElapsedMs(0);
      return;
    }

    recorder.stop();
  }

  async function handleToggleRecord() {
    if (!consultation) {
      return;
    }

    if (isSubmittingResponse || state.loading) {
      return;
    }

    if (isRecording) {
      stopBrowserRecording();
      return;
    }

    if (consultation.status !== "waiting_user_input") {
      pushToast("当前还未进入回答窗口，需要先完成本轮问题视频播放。", "warning");
      return;
    }

    await startBrowserRecording();
  }

  async function handleEnd() {
    if (!consultation) {
      return;
    }

    const createdAssessment = await actions.handleStartAssessment();
    if (!createdAssessment) {
      pushToast("测试模式：量表会话未创建成功，先进入量表页面。", "warning");
    }
    navigate(APP_PATHS.assessment, { state: { sessionId: consultation.session_id } });
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

  return (
    <ConsultationLayout backgroundImage="/4K.png" title="智能评估">
      <div className="absolute inset-x-0 top-0 z-50 pointer-events-none">
        <div className="pointer-events-auto">
          <ConsultationProgress currentStageOrder={currentStageOrder} steps={STAGE_LABELS} />
        </div>
      </div>

      <AppToast toast={toast} />

      <div className="flex w-full h-full relative z-10 bg-transparent pt-8 overflow-hidden [perspective:2000px]">
        <div
          className="flex-1 relative h-full flex flex-col items-center transition-all duration-[800ms] min-h-0 perspective-[1200px]"
          style={{ marginRight: isOpen ? "min(45vw, 650px)" : "0px" }}
        >
          <div className="flex-1 w-full max-w-[1200px] mx-auto flex flex-col items-center justify-end relative mt-2 z-10 pointer-events-none">
            {playableVideoUri ? (
              <div className="relative flex w-full items-end justify-center">
                <video
                  ref={videoRef}
                  key={`${consultation.current_prompt_key || "current"}:${playableVideoUri}`}
                  src={playableVideoUri}
                  className="h-[min(84vh,920px)] w-auto max-w-[82vw] object-contain [background:transparent] drop-shadow-[0_28px_60px_rgba(15,23,42,0.28)] -translate-y-10 md:-translate-y-16 scale-[1.08] md:scale-[1.15]"
                  playsInline
                  preload="auto"
                  onEnded={handleVideoEnded}
                  onError={() => {
                    setVideoError("当前视频资源加载失败，请稍后重试。");
                    setPlaybackBlocked(false);
                  }}
                />

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

                {isCompletingSystemQuestion ? (
                  <div className="absolute inset-0 z-20 flex items-center justify-center">
                    <div className="inline-flex items-center gap-3 rounded-full border border-white/15 bg-black/35 px-5 py-3 text-sm text-white shadow-lg backdrop-blur-xl">
                      <LoaderCircle className="h-4 w-4 animate-spin" />
                      正在自动推进到下一题
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="mb-28 flex min-h-[48vh] w-full max-w-[820px] flex-col items-center justify-center gap-4 rounded-[2rem] border border-white/12 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.18),transparent_38%),linear-gradient(135deg,rgba(15,23,42,0.68),rgba(15,23,42,0.42))] px-8 text-center text-white backdrop-blur-md">
                <div className="flex h-20 w-20 items-center justify-center rounded-full border border-white/15 bg-white/8">
                  <VideoOff className="h-8 w-8 text-sky-100/80" />
                </div>
                <div className="space-y-2">
                  <p className="text-xl font-medium">当前题目的视频资源尚未接入</p>
                  <p className="max-w-2xl text-sm leading-7 text-slate-200/80">
                    真实会话状态已经接通，但当前阶段的 manifest 仍未提供可播放视频 URI。
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="absolute bottom-4 md:bottom-5 inset-x-0 z-20 flex flex-col items-center w-full gap-[10px] pb-0 pointer-events-auto shadow-sm">
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
              endDisabled={isRecording || isSubmittingResponse}
              recordLabel={isRecording ? `结束录音 ${formatDuration(recordingElapsedMs)}` : "开始录音"}
            />
          </div>

          <div className="absolute left-[5%] lg:left-[10%] top-1/2 -translate-y-[40%] z-[100] pointer-events-none w-[240px] sm:w-[280px] flex items-center justify-center">
            <DraggableMessagePanel title="实时字幕" message={dialoguePanelMessage} />
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
                  <ConsultationStatusPanel
                    consultation={consultation}
                    onRefresh={handleRefresh}
                    refreshing={state.loading}
                    isRecording={isRecording}
                    cameraStream={cameraStream}
                    cameraReady={cameraReady}
                    cameraError={cameraError}
                    localTranscript={liveTranscriptText}
                    className="h-full"
                  />
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
            detailText={cameraReady ? "摄像头已接入，正在采样" : "等待摄像头授权"}
            errorText={cameraError}
          />
        </div>
      </div>
    </ConsultationLayout>
  );
}
