import {
  forwardRef,
  useEffect,
  useEffectEvent,
  useImperativeHandle,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";

import { cn } from "../../lib/utils";

export type SeamlessVideoClip = {
  clipKey: string;
  src: string;
  label?: string;
  poster?: string | null;
};

type LayerId = "A" | "B";
type LayerPhase = "idle" | "loading" | "ready" | "error";

type SeamlessVideoLayerState = {
  clipKey: string | null;
  phase: LayerPhase;
  isActive: boolean;
  isReady: boolean;
  isVisible: boolean;
};

export type SeamlessVideoPlayerState = {
  activeLayerId: LayerId;
  displayedClipKey: string | null;
  preloadClipKey: string | null;
  layers: Record<LayerId, SeamlessVideoLayerState>;
};

export type SeamlessVideoPlaybackBlockedEvent = {
  clip: SeamlessVideoClip;
  error: unknown;
};

export type SeamlessVideoErrorEvent = {
  clip: SeamlessVideoClip | null;
  errorEvent: SyntheticEvent<HTMLVideoElement, Event>;
  layerId: LayerId;
};

export type SeamlessVideoTimeUpdateEvent = {
  clip: SeamlessVideoClip;
  video: HTMLVideoElement;
};

export type SeamlessVideoPlayerHandle = {
  getDisplayedVideoElement: () => HTMLVideoElement | null;
  getPreloadVideoElement: () => HTMLVideoElement | null;
  pauseDisplayed: () => void;
  playDisplayed: () => Promise<void>;
};

export type SeamlessVideoPlayerProps = {
  currentClip: SeamlessVideoClip | null;
  preloadClip?: SeamlessVideoClip | null;
  className?: string;
  controls?: boolean;
  loop?: boolean;
  muted?: boolean;
  autoPlay?: boolean;
  playsInline?: boolean;
  transitionDurationMs?: number;
  layerClassName?: string;
  videoClassName?: string;
  onClipReady?: (clip: SeamlessVideoClip) => void;
  onDisplayedClipChange?: (clip: SeamlessVideoClip | null) => void;
  onEnded?: (clip: SeamlessVideoClip) => void;
  onPlaybackBlocked?: (event: SeamlessVideoPlaybackBlockedEvent) => void;
  onPlaybackStarted?: (clip: SeamlessVideoClip) => void;
  onStateChange?: (state: SeamlessVideoPlayerState) => void;
  onTimeUpdate?: (event: SeamlessVideoTimeUpdateEvent) => void;
  onVideoError?: (event: SeamlessVideoErrorEvent) => void;
};

type FrameAwareVideoElement = HTMLVideoElement & {
  cancelVideoFrameCallback?: (handle: number) => void;
  requestVideoFrameCallback?: (callback: (now: number, metadata: unknown) => void) => number;
};

const LAYER_IDS: LayerId[] = ["A", "B"];
const FRAME_READY_TIMEOUT_MS = 900;

function buildClipSignature(clip: SeamlessVideoClip | null | undefined) {
  return clip ? `${clip.clipKey}::${clip.src}` : "";
}

function getOtherLayerId(layerId: LayerId): LayerId {
  return layerId === "A" ? "B" : "A";
}

export const SeamlessVideoPlayer = forwardRef<SeamlessVideoPlayerHandle, SeamlessVideoPlayerProps>(
  function SeamlessVideoPlayer(
    {
      currentClip,
      preloadClip = null,
      className,
      controls = false,
      loop = false,
      muted = false,
      autoPlay = true,
      playsInline = true,
      transitionDurationMs = 220,
      layerClassName,
      videoClassName,
      onClipReady,
      onDisplayedClipChange,
      onEnded,
      onPlaybackBlocked,
      onPlaybackStarted,
      onStateChange,
      onTimeUpdate,
      onVideoError,
    },
    ref,
  ) {
    const videoRefs = {
      A: useRef<HTMLVideoElement | null>(null),
      B: useRef<HTMLVideoElement | null>(null),
    };

    const activeLayerIdRef = useRef<LayerId>("A");
    const displayedClipRef = useRef<SeamlessVideoClip | null>(null);
    const currentClipRef = useRef<SeamlessVideoClip | null>(currentClip);
    const preloadClipRef = useRef<SeamlessVideoClip | null>(preloadClip);
    const layerClipRef = useRef<Record<LayerId, SeamlessVideoClip | null>>({ A: null, B: null });
    const layerClipSignatureRef = useRef<Record<LayerId, string>>({ A: "", B: "" });
    const layerReadyRef = useRef<Record<LayerId, boolean>>({ A: false, B: false });
    const layerPhaseRef = useRef<Record<LayerId, LayerPhase>>({ A: "idle", B: "idle" });
    const frameCallbackHandleRef = useRef<Record<LayerId, number | null>>({ A: null, B: null });
    const frameReadyTimeoutRef = useRef<Record<LayerId, number | null>>({ A: null, B: null });
    const transitionTimerRef = useRef<number | null>(null);

    const [activeLayerId, setActiveLayerId] = useState<LayerId>("A");

    const emitStateChange = useEffectEvent(() => {
      if (!onStateChange) {
        return;
      }

      const currentPreloadClip = preloadClipRef.current;
      const currentActiveLayerId = activeLayerIdRef.current;

      onStateChange({
        activeLayerId: currentActiveLayerId,
        displayedClipKey: displayedClipRef.current?.clipKey ?? null,
        preloadClipKey: currentPreloadClip?.clipKey ?? null,
        layers: {
          A: {
            clipKey: layerClipRef.current.A?.clipKey ?? null,
            phase: layerPhaseRef.current.A,
            isActive: currentActiveLayerId === "A",
            isReady: layerReadyRef.current.A,
            isVisible: currentActiveLayerId === "A",
          },
          B: {
            clipKey: layerClipRef.current.B?.clipKey ?? null,
            phase: layerPhaseRef.current.B,
            isActive: currentActiveLayerId === "B",
            isReady: layerReadyRef.current.B,
            isVisible: currentActiveLayerId === "B",
          },
        },
      });
    });

    const clearFrameReadyWait = useEffectEvent((layerId: LayerId) => {
      const videoElement = videoRefs[layerId].current as FrameAwareVideoElement | null;
      const frameHandle = frameCallbackHandleRef.current[layerId];
      if (videoElement?.cancelVideoFrameCallback && frameHandle !== null) {
        videoElement.cancelVideoFrameCallback(frameHandle);
      }
      frameCallbackHandleRef.current[layerId] = null;

      const timeoutId = frameReadyTimeoutRef.current[layerId];
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
      frameReadyTimeoutRef.current[layerId] = null;
    });

    const updateLayerPhase = useEffectEvent((layerId: LayerId, phase: LayerPhase) => {
      layerPhaseRef.current[layerId] = phase;
      emitStateChange();
    });

    const updateDisplayedClip = useEffectEvent((clip: SeamlessVideoClip | null) => {
      const nextSignature = buildClipSignature(clip);
      const currentSignature = buildClipSignature(displayedClipRef.current);
      if (nextSignature === currentSignature) {
        return;
      }

      displayedClipRef.current = clip;
      onDisplayedClipChange?.(clip);
      emitStateChange();
    });

    const getVideoElement = useEffectEvent((layerId: LayerId) => videoRefs[layerId].current);

    const pauseLayer = useEffectEvent((layerId: LayerId) => {
      const videoElement = getVideoElement(layerId);
      videoElement?.pause();
    });

    const attemptPlayLayer = useEffectEvent(async (layerId: LayerId) => {
      if (!autoPlay) {
        return;
      }

      const clip = layerClipRef.current[layerId];
      const videoElement = getVideoElement(layerId);
      if (!clip || !videoElement) {
        return;
      }

      try {
        await videoElement.play();
        onPlaybackStarted?.(clip);
      } catch (error) {
        onPlaybackBlocked?.({ clip, error });
      }
    });

    const switchDisplayedLayer = useEffectEvent((nextLayerId: LayerId) => {
      const nextClip = layerClipRef.current[nextLayerId];
      if (!nextClip) {
        return;
      }

      const previousLayerId = activeLayerIdRef.current;
      const isSwitchingLayers = previousLayerId !== nextLayerId;

      void attemptPlayLayer(nextLayerId);
      activeLayerIdRef.current = nextLayerId;
      setActiveLayerId(nextLayerId);
      updateDisplayedClip(nextClip);

      if (transitionTimerRef.current !== null) {
        window.clearTimeout(transitionTimerRef.current);
      }

      if (isSwitchingLayers) {
        transitionTimerRef.current = window.setTimeout(() => {
          pauseLayer(previousLayerId);
          transitionTimerRef.current = null;
        }, transitionDurationMs + 48);
      }

      emitStateChange();
    });

    const handleLayerReady = useEffectEvent((layerId: LayerId) => {
      const clip = layerClipRef.current[layerId];
      if (!clip || layerReadyRef.current[layerId]) {
        return;
      }

      layerReadyRef.current[layerId] = true;
      updateLayerPhase(layerId, "ready");
      onClipReady?.(clip);

      const desiredCurrentSignature = buildClipSignature(currentClipRef.current);
      const layerSignature = layerClipSignatureRef.current[layerId];
      if (!desiredCurrentSignature || desiredCurrentSignature !== layerSignature) {
        emitStateChange();
        return;
      }

      if (activeLayerIdRef.current === layerId) {
        updateDisplayedClip(clip);
        void attemptPlayLayer(layerId);
        return;
      }

      switchDisplayedLayer(layerId);
    });

    const scheduleFrameReadyCheck = useEffectEvent((layerId: LayerId) => {
      const videoElement = getVideoElement(layerId) as FrameAwareVideoElement | null;
      const assignedSignature = layerClipSignatureRef.current[layerId];
      if (!videoElement || !assignedSignature) {
        return;
      }

      clearFrameReadyWait(layerId);

      const finalizeReady = () => {
        if (assignedSignature !== layerClipSignatureRef.current[layerId]) {
          return;
        }
        if (videoElement.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
          return;
        }
        handleLayerReady(layerId);
      };

      frameReadyTimeoutRef.current[layerId] = window.setTimeout(() => {
        finalizeReady();
        frameReadyTimeoutRef.current[layerId] = null;
      }, FRAME_READY_TIMEOUT_MS);

      if (videoElement.requestVideoFrameCallback) {
        frameCallbackHandleRef.current[layerId] = videoElement.requestVideoFrameCallback(() => {
          finalizeReady();
          frameCallbackHandleRef.current[layerId] = null;
        });
        return;
      }

      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          finalizeReady();
        });
      });
    });

    const loadClipIntoLayer = useEffectEvent((layerId: LayerId, clip: SeamlessVideoClip | null) => {
      const videoElement = getVideoElement(layerId);
      const nextSignature = buildClipSignature(clip);
      const currentSignature = layerClipSignatureRef.current[layerId];

      if (nextSignature === currentSignature) {
        if (clip && layerReadyRef.current[layerId] && buildClipSignature(currentClipRef.current) === nextSignature) {
          if (activeLayerIdRef.current === layerId) {
            updateDisplayedClip(clip);
            void attemptPlayLayer(layerId);
          } else {
            switchDisplayedLayer(layerId);
          }
        }
        return;
      }

      clearFrameReadyWait(layerId);
      layerClipRef.current[layerId] = clip;
      layerClipSignatureRef.current[layerId] = nextSignature;
      layerReadyRef.current[layerId] = false;

      if (!clip || !videoElement) {
        updateLayerPhase(layerId, "idle");
        if (videoElement) {
          videoElement.pause();
          videoElement.removeAttribute("src");
          videoElement.removeAttribute("poster");
          videoElement.load();
        }
        return;
      }

      updateLayerPhase(layerId, "loading");
      videoElement.pause();
      if (clip.poster) {
        videoElement.poster = clip.poster;
      } else {
        videoElement.removeAttribute("poster");
      }
      videoElement.src = clip.src;
      videoElement.load();
    });

    const syncCurrentClip = useEffectEvent((clip: SeamlessVideoClip | null) => {
      currentClipRef.current = clip;

      if (!clip) {
        loadClipIntoLayer("A", null);
        loadClipIntoLayer("B", null);
        updateDisplayedClip(null);
        emitStateChange();
        return;
      }

      const currentSignature = buildClipSignature(clip);
      const activeLayerSignature = layerClipSignatureRef.current[activeLayerIdRef.current];
      const inactiveLayerId = getOtherLayerId(activeLayerIdRef.current);
      const inactiveLayerSignature = layerClipSignatureRef.current[inactiveLayerId];

      if (activeLayerSignature === currentSignature) {
        if (layerReadyRef.current[activeLayerIdRef.current]) {
          updateDisplayedClip(clip);
          void attemptPlayLayer(activeLayerIdRef.current);
        } else {
          loadClipIntoLayer(activeLayerIdRef.current, clip);
        }
        return;
      }

      if (inactiveLayerSignature === currentSignature) {
        if (layerReadyRef.current[inactiveLayerId]) {
          switchDisplayedLayer(inactiveLayerId);
        }
        return;
      }

      const targetLayerId = displayedClipRef.current ? inactiveLayerId : activeLayerIdRef.current;
      loadClipIntoLayer(targetLayerId, clip);
    });

    const syncPreloadClip = useEffectEvent((nextClip: SeamlessVideoClip | null) => {
      preloadClipRef.current = nextClip;

      if (!nextClip) {
        emitStateChange();
        return;
      }

      const preloadSignature = buildClipSignature(nextClip);
      const currentSignature = buildClipSignature(currentClipRef.current);
      if (preloadSignature === currentSignature) {
        emitStateChange();
        return;
      }

      const activeLayerIdNow = activeLayerIdRef.current;
      const inactiveLayerId = getOtherLayerId(activeLayerIdNow);
      const activeLayerSignature = layerClipSignatureRef.current[activeLayerIdNow];
      const inactiveLayerSignature = layerClipSignatureRef.current[inactiveLayerId];

      if (activeLayerSignature === preloadSignature || inactiveLayerSignature === preloadSignature) {
        emitStateChange();
        return;
      }

      loadClipIntoLayer(inactiveLayerId, nextClip);
    });

    useImperativeHandle(ref, () => ({
      getDisplayedVideoElement: () => getVideoElement(activeLayerIdRef.current),
      getPreloadVideoElement: () => getVideoElement(getOtherLayerId(activeLayerIdRef.current)),
      pauseDisplayed: () => {
        pauseLayer(activeLayerIdRef.current);
      },
      playDisplayed: async () => {
        const videoElement = getVideoElement(activeLayerIdRef.current);
        if (!videoElement) {
          return;
        }

        const clip = layerClipRef.current[activeLayerIdRef.current];
        try {
          await videoElement.play();
          if (clip) {
            onPlaybackStarted?.(clip);
          }
        } catch (error) {
          if (clip) {
            onPlaybackBlocked?.({ clip, error });
          }
          throw error;
        }
      },
    }));

    useEffect(() => {
      syncCurrentClip(currentClip);
    }, [currentClip]);

    useEffect(() => {
      syncPreloadClip(preloadClip);
    }, [preloadClip]);

    useEffect(() => {
      return () => {
        LAYER_IDS.forEach((layerId) => {
          clearFrameReadyWait(layerId);
          pauseLayer(layerId);
          const videoElement = videoRefs[layerId].current;
          if (videoElement) {
            videoElement.removeAttribute("src");
            videoElement.removeAttribute("poster");
            videoElement.load();
          }
        });

        if (transitionTimerRef.current !== null) {
          window.clearTimeout(transitionTimerRef.current);
        }
      };
    }, []);

    const handleLoadedState = useEffectEvent((layerId: LayerId) => {
      if (!layerClipRef.current[layerId]) {
        return;
      }
      scheduleFrameReadyCheck(layerId);
    });

    const handleVideoEnded = useEffectEvent((layerId: LayerId) => {
      if (activeLayerIdRef.current !== layerId) {
        return;
      }

      const clip = layerClipRef.current[layerId];
      if (!clip) {
        return;
      }

      onEnded?.(clip);
    });

    const handleVideoTimeUpdate = useEffectEvent((layerId: LayerId) => {
      if (activeLayerIdRef.current !== layerId) {
        return;
      }

      const clip = layerClipRef.current[layerId];
      const videoElement = getVideoElement(layerId);
      if (!clip || !videoElement) {
        return;
      }

      onTimeUpdate?.({ clip, video: videoElement });
    });

    const handleVideoError = useEffectEvent((layerId: LayerId, errorEvent: SyntheticEvent<HTMLVideoElement, Event>) => {
      layerReadyRef.current[layerId] = false;
      updateLayerPhase(layerId, "error");
      onVideoError?.({
        clip: layerClipRef.current[layerId],
        errorEvent,
        layerId,
      });
    });

    const sharedLayerClassName =
      "absolute inset-0 transition-opacity will-change-[opacity] motion-reduce:transition-none";
    const sharedVideoClassName = "h-full w-full object-contain [background:transparent]";

    return (
      <div className={cn("relative isolate overflow-hidden", className)}>
        {LAYER_IDS.map((layerId) => {
          const isVisible = activeLayerId === layerId;

          return (
            <div
              key={layerId}
              aria-hidden={!isVisible}
              className={cn(
                sharedLayerClassName,
                isVisible ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
                layerClassName,
              )}
              style={{ transitionDuration: `${transitionDurationMs}ms` }}
            >
              <video
                ref={videoRefs[layerId]}
                controls={controls}
                loop={loop}
                muted={muted}
                playsInline={playsInline}
                preload="auto"
                className={cn(sharedVideoClassName, videoClassName)}
                onCanPlay={() => handleLoadedState(layerId)}
                onEnded={() => handleVideoEnded(layerId)}
                onError={(event) => handleVideoError(layerId, event)}
                onLoadedData={() => handleLoadedState(layerId)}
                onTimeUpdate={() => handleVideoTimeUpdate(layerId)}
              />
            </div>
          );
        })}
      </div>
    );
  },
);
