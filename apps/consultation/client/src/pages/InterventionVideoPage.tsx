import { useEffect, useEffectEvent, useLayoutEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RotateCcw, X } from "lucide-react";

import { useInterventionExecution } from "../features/intervention/useInterventionExecution";
import { APP_PATHS } from "../routes";

const OCEAN_VIDEO_SRC = "/intervention/video/ocean-h264.mp4";
const CONTROLS_HIDE_DELAY_MS = 3_000;

type FullscreenElement = HTMLDivElement & {
  webkitRequestFullscreen?: () => Promise<void> | void;
};

type FullscreenDocument = Document & {
  webkitExitFullscreen?: () => Promise<void> | void;
  webkitFullscreenElement?: Element | null;
};

async function requestPlayerFullscreen(element: HTMLDivElement | null) {
  if (!element) {
    return;
  }

  const fullscreenElement = element as FullscreenElement;

  if (fullscreenElement.requestFullscreen) {
    await fullscreenElement.requestFullscreen();
    return;
  }

  await fullscreenElement.webkitRequestFullscreen?.();
}

async function exitPlayerFullscreen() {
  const fullscreenDocument = document as FullscreenDocument;

  if (document.fullscreenElement && document.exitFullscreen) {
    await document.exitFullscreen();
    return;
  }

  await fullscreenDocument.webkitExitFullscreen?.();
}

export default function InterventionVideoPage() {
  const navigate = useNavigate();
  const { buildRouteState, trackEvent } = useInterventionExecution({
    pageTag: "intervention-video",
    openEvent: {
      event_type: "experience_opened",
      program_id: "ocean",
      program_title: "海洋",
      delivery_mode: "video",
      payload: { page: "intervention-video", video_src: OCEAN_VIDEO_SRC },
    },
  });
  const playerShellRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const hideControlsTimerRef = useRef<number | null>(null);
  const [areControlsVisible, setAreControlsVisible] = useState(false);

  const clearControlsHideTimer = () => {
    if (hideControlsTimerRef.current !== null) {
      window.clearTimeout(hideControlsTimerRef.current);
      hideControlsTimerRef.current = null;
    }
  };

  const showControls = useEffectEvent(() => {
    clearControlsHideTimer();
    setAreControlsVisible(true);
    hideControlsTimerRef.current = window.setTimeout(() => {
      setAreControlsVisible(false);
      hideControlsTimerRef.current = null;
    }, CONTROLS_HIDE_DELAY_MS);
  });

  const startPlayback = useEffectEvent(async () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    try {
      await video.play();
    } catch {
      // A user touch reveals the controls and lets the visitor retry playback.
    }
  });

  useLayoutEffect(() => {
    void requestPlayerFullscreen(playerShellRef.current).catch(() => undefined);
    void startPlayback();
  }, [startPlayback]);

  useEffect(
    () => () => {
      clearControlsHideTimer();
      videoRef.current?.pause();
    },
    [],
  );

  const handleSurfaceInteraction = () => {
    showControls();
    void requestPlayerFullscreen(playerShellRef.current).catch(() => undefined);

    if (videoRef.current?.paused) {
      void startPlayback();
    }
  };

  const handleReplay = async () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    showControls();
    video.currentTime = 0;
    await startPlayback();
  };

  const handleExit = () => {
    void trackEvent({
      event_type: "experience_exited",
      program_id: "ocean",
      program_title: "海洋",
      delivery_mode: "video",
      payload: { page: "intervention-video", reason: "exit_button" },
    });
    void exitPlayerFullscreen().catch(() => undefined);
    navigate(APP_PATHS.intervention, { state: buildRouteState() });
  };

  return (
    <div
      ref={playerShellRef}
      className="fixed inset-0 overflow-hidden bg-black"
      onPointerDown={handleSurfaceInteraction}
    >
      <video
        ref={videoRef}
        src={OCEAN_VIDEO_SRC}
        className="h-full w-full object-cover"
        playsInline
        loop
        preload="auto"
      />

      {areControlsVisible ? (
        <div className="absolute inset-x-0 bottom-0 flex justify-center bg-gradient-to-t from-black/75 via-black/30 to-transparent px-6 pb-8 pt-24">
          <div className="flex items-center gap-4 rounded-full border border-white/20 bg-black/45 p-3 backdrop-blur-md">
            <button
              type="button"
              aria-label="重新播放"
              onClick={() => void handleReplay()}
              className="flex h-12 items-center justify-center gap-2 rounded-full bg-white/15 px-4 text-sm text-white transition hover:bg-white/25"
            >
              <RotateCcw size={21} />
              <span>重新播放</span>
            </button>
            <button
              type="button"
              aria-label="退出"
              onClick={handleExit}
              className="flex h-12 items-center justify-center gap-2 rounded-full bg-white/15 px-4 text-sm text-white transition hover:bg-white/25"
            >
              <X size={23} />
              <span>退出</span>
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
