import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";
import { PlayCircle } from "lucide-react";

import {
  SeamlessVideoPlayer,
  type SeamlessVideoClip,
  type SeamlessVideoPlayerHandle,
} from "../../../components/video";
import { cn } from "../../../lib/utils";

interface DigitalCounselorProps {
  imageSrc?: string;
  title?: string;
  className?: string;
  overallSeverity?: string | null;
}

const RESULT_VIDEO_WAIT_MS = 5000;
const RESULT_INTRO_CLIP: SeamlessVideoClip = {
  clipKey: "result-intro-001",
  src: "/digital-human/result-v1/result-intro-001.webm",
  label: "请看您的测评结果",
};

const RESULT_SEVERITY_CLIPS: Record<"none" | "mild" | "moderate" | "severe", SeamlessVideoClip> = {
  none: {
    clipKey: "result-severity-none-001",
    src: "/digital-human/result-v1/result-severity-none-001.webm",
    label: "您的报告结果显示为无抑郁",
  },
  mild: {
    clipKey: "result-severity-mild-001",
    src: "/digital-human/result-v1/result-severity-mild-001.webm",
    label: "您的报告结果显示为轻度抑郁",
  },
  moderate: {
    clipKey: "result-severity-moderate-001",
    src: "/digital-human/result-v1/result-severity-moderate-001.webm",
    label: "您的报告结果显示为中度抑郁",
  },
  severe: {
    clipKey: "result-severity-severe-001",
    src: "/digital-human/result-v1/result-severity-severe-001.webm",
    label: "您的报告结果显示为重度抑郁",
  },
};

const RESULT_VIDEO_CLASS_NAME =
  "relative z-10 block h-auto max-h-[calc(100vh-140px)] w-full max-w-[clamp(380px,28vw,560px)] origin-bottom scale-[2.66] translate-y-[400px] select-none object-contain object-bottom drop-shadow-[0_24px_48px_rgba(15,23,42,0.28)] xl:max-h-[calc(100vh-132px)] xl:scale-[2.86] xl:translate-y-[424px]";

const RESULT_FALLBACK_IMAGE_CLASS_NAME =
  "relative z-10 block h-auto max-h-[calc(100vh-160px)] w-full max-w-[clamp(380px,28vw,560px)] origin-bottom scale-[1.63] translate-y-[260px] select-none object-contain object-bottom drop-shadow-[0_24px_48px_rgba(15,23,42,0.28)] xl:max-h-[calc(100vh-148px)] xl:scale-[1.74] xl:translate-y-[276px]";

function resolveSeverityClip(overallSeverity?: string | null) {
  const normalized = String(overallSeverity || "").trim().toLowerCase();
  if (!normalized) {
    return null;
  }

  if (
    normalized.includes("中重度") ||
    normalized.includes("重度") ||
    normalized.includes("危险") ||
    normalized.includes("高风险") ||
    normalized.includes("severe")
  ) {
    return RESULT_SEVERITY_CLIPS.severe;
  }

  if (normalized.includes("中度") || normalized.includes("moderate")) {
    return RESULT_SEVERITY_CLIPS.moderate;
  }

  if (normalized.includes("轻度") || normalized.includes("mild")) {
    return RESULT_SEVERITY_CLIPS.mild;
  }

  if (
    normalized.includes("无") ||
    normalized.includes("正常") ||
    normalized.includes("极轻") ||
    normalized.includes("minimal")
  ) {
    return RESULT_SEVERITY_CLIPS.none;
  }

  return null;
}

export function DigitalCounselor({
  imageSrc = "/home-digital-human.png",
  title = "数字心理咨询师",
  className,
  overallSeverity,
}: DigitalCounselorProps) {
  const playerRef = useRef<SeamlessVideoPlayerHandle | null>(null);
  const waitTimerRef = useRef<number | null>(null);
  const [sequenceStep, setSequenceStep] = useState<"intro" | "severity">("intro");
  const [playbackBlocked, setPlaybackBlocked] = useState(false);
  const [videoError, setVideoError] = useState(false);

  const severityClip = useMemo(
    () => resolveSeverityClip(overallSeverity),
    [overallSeverity],
  );
  const currentClip = sequenceStep === "severity" ? severityClip : RESULT_INTRO_CLIP;
  const preloadClip = sequenceStep === "intro" ? severityClip : null;

  const clearWaitTimer = () => {
    if (waitTimerRef.current !== null) {
      window.clearTimeout(waitTimerRef.current);
      waitTimerRef.current = null;
    }
  };

  useEffect(() => {
    clearWaitTimer();
    setSequenceStep("intro");
    setPlaybackBlocked(false);
    setVideoError(false);
  }, [overallSeverity]);

  useEffect(() => {
    return () => {
      clearWaitTimer();
    };
  }, []);

  const handleVideoEnded = useEffectEvent((clip: SeamlessVideoClip) => {
    if (clip.clipKey !== RESULT_INTRO_CLIP.clipKey || !severityClip) {
      return;
    }

    clearWaitTimer();
    waitTimerRef.current = window.setTimeout(() => {
      setSequenceStep("severity");
    }, RESULT_VIDEO_WAIT_MS);
  });

  async function handleResumePlayback() {
    const player = playerRef.current;
    if (!player) {
      return;
    }

    try {
      await player.playDisplayed();
      setPlaybackBlocked(false);
    } catch {
      setPlaybackBlocked(true);
    }
  }

  if (videoError) {
    return (
      <div className={cn("flex h-full w-full items-end justify-center overflow-hidden", className)}>
        <img
          src={imageSrc}
          alt={title}
          className={RESULT_FALLBACK_IMAGE_CLASS_NAME}
          draggable={false}
        />
      </div>
    );
  }

  return (
    <div className={cn("flex h-full w-full items-end justify-center overflow-hidden", className)}>
      <div className="relative h-full w-full">
        <SeamlessVideoPlayer
          ref={playerRef}
          currentClip={currentClip}
          preloadClip={preloadClip}
          className="h-full w-full"
          transitionDurationMs={0}
          videoClassName={RESULT_VIDEO_CLASS_NAME}
          muted={false}
          playsInline
          onEnded={handleVideoEnded}
          onPlaybackBlocked={() => {
            setPlaybackBlocked(true);
          }}
          onVideoError={() => {
            setVideoError(true);
          }}
        />
        {playbackBlocked ? (
          <button
            type="button"
            onClick={() => {
              void handleResumePlayback();
            }}
            className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/18"
            aria-label="播放结果视频"
          >
            <span className="inline-flex items-center gap-3 rounded-full border border-white/30 bg-slate-950/55 px-5 py-3 text-white shadow-[0_18px_40px_rgba(15,23,42,0.3)] backdrop-blur">
              <PlayCircle className="h-6 w-6" />
              点击播放结果视频
            </span>
          </button>
        ) : null}
      </div>
    </div>
  );
}
