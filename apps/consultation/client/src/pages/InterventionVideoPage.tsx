import { useEffect, useEffectEvent, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Maximize2,
  Minimize2,
  Pause,
  Play,
  RotateCcw,
  SlidersHorizontal,
  Volume2,
  VolumeX,
} from "lucide-react";

import { useInterventionExecution } from "../features/intervention/useInterventionExecution";
import { INTERVENTION_VIDEO_PROGRAMS, type InterventionVideoProgram } from "../features/intervention/videoPrograms";
import { ConsultationLayout } from "../layouts";
import { APP_PATHS } from "../routes";

type FullscreenElement = HTMLDivElement & {
  webkitRequestFullscreen?: () => Promise<void> | void;
};

type FullscreenDocument = Document & {
  webkitExitFullscreen?: () => Promise<void> | void;
  webkitFullscreenElement?: Element | null;
};

const COPY = {
  pageTitle: "\u89c6\u9891\u8c03\u8282",
  heroTitle: "\u770b\u4e00\u6bb5\u89c6\u9891",
  backHome: "\u8fd4\u56de\u5e72\u9884\u9996\u9875",
  playbackCardLabel: "\u5f53\u524d\u64ad\u653e",
  emptyProgram: "\u8bf7\u9009\u62e9\u4e00\u4e2a\u89c6\u9891\u5f00\u59cb\u64ad\u653e",
  emptyHint:
    "\u9009\u62e9\u89c6\u9891\u540e\u5c06\u94fa\u6ee1\u5f71\u9662\u94f6\u5e55\u64ad\u653e\u3002\u9700\u8981\u5168\u5c4f\u65f6\uff0c\u8bf7\u70b9\u51fb\u53f3\u4e0a\u89d2\u7684\u5168\u5c4f\u6309\u94ae\u3002",
  panelTitle: "\u63a7\u5236\u9762\u677f",
  progressLabel: "\u64ad\u653e\u8fdb\u5ea6",
  volumeLabel: "\u97f3\u91cf",
  replay: "\u4ece\u5934\u64ad\u653e",
  moreControlsOpen: "\u5c55\u5f00\u66f4\u591a\u63a7\u5236",
  moreControlsClose: "\u6536\u8d77\u66f4\u591a\u63a7\u5236",
  enterFullscreen: "\u8fdb\u5165\u5168\u5c4f",
  exitFullscreen: "\u9000\u51fa\u5168\u5c4f",
  pause: "\u6682\u505c\u64ad\u653e",
  resume: "\u7ee7\u7eed\u64ad\u653e",
  restoreVolume: "\u6062\u590d\u97f3\u91cf",
  mute: "\u9759\u97f3",
  selectionTitle: "\u9009\u62e9\u4e00\u4e2a\u89c6\u9891",
  selectionHint:
    "\u9009\u62e9\u4efb\u610f\u4e00\u4e2a\u89c6\u9891\u540e\uff0c\u89c6\u9891\u4f1a\u94fa\u6ee1\u5f71\u9662\u94f6\u5e55\u64ad\u653e\u3002\u53ef\u4ee5\u6309\u9700\u6682\u505c\u3001\u62d6\u52a8\u8fdb\u5ea6\u3001\u8c03\u6574\u97f3\u91cf\uff0c\u6216\u70b9\u51fb\u5168\u5c4f\u6309\u94ae\u3002",
  changeProgram: "\u5207\u6362\u89c6\u9891",
  cannotFullscreen: "\u672a\u80fd\u8fdb\u5165\u5168\u5c4f\uff0c\u4f46\u89c6\u9891\u5df2\u7ecf\u5f00\u59cb\u64ad\u653e\u3002",
  playbackBlocked: "\u6d4f\u89c8\u5668\u62e6\u622a\u4e86\u64ad\u653e\uff0c\u8bf7\u70b9\u51fb\u7ee7\u7eed\u64ad\u653e\u91cd\u8bd5\u3002",
  cannotReenterFullscreen: "\u5f53\u524d\u6d4f\u89c8\u5668\u672a\u80fd\u518d\u6b21\u8fdb\u5165\u5168\u5c4f\u3002",
  controlPanelOpen: "\u5c55\u5f00\u66f4\u591a\u63a7\u5236",
  controlPanelClose: "\u6536\u8d77\u66f4\u591a\u63a7\u5236",
} as const;

function toAssetUri(path: string) {
  return encodeURI(path);
}

function getLoopedAudioTime(audio: HTMLAudioElement, videoTime: number) {
  if (!Number.isFinite(audio.duration) || audio.duration <= 0) {
    return 0;
  }
  return Math.max(0, videoTime % audio.duration);
}

function formatDuration(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "00:00";
  }

  const totalSeconds = Math.floor(seconds);
  const minutes = Math.floor(totalSeconds / 60);
  const remainSeconds = totalSeconds % 60;

  return `${String(minutes).padStart(2, "0")}:${String(remainSeconds).padStart(2, "0")}`;
}

async function requestPlayerFullscreen(element: HTMLDivElement | null) {
  if (!element) {
    return;
  }

  const fullscreenElement = element as FullscreenElement;

  if (fullscreenElement.requestFullscreen) {
    await fullscreenElement.requestFullscreen();
    return;
  }

  if (fullscreenElement.webkitRequestFullscreen) {
    await fullscreenElement.webkitRequestFullscreen();
  }
}

async function exitPlayerFullscreen() {
  const fullscreenDocument = document as FullscreenDocument;

  if (document.fullscreenElement && document.exitFullscreen) {
    await document.exitFullscreen();
    return;
  }

  if (fullscreenDocument.webkitFullscreenElement && fullscreenDocument.webkitExitFullscreen) {
    await fullscreenDocument.webkitExitFullscreen();
  }
}

export default function InterventionVideoPage() {
  const navigate = useNavigate();
  const { buildRouteState, sessionError, trackEvent } = useInterventionExecution({
    pageTag: "intervention-video",
    openEvent: {
      event_type: "experience_opened",
      program_id: "video-regulation",
      program_title: COPY.pageTitle,
      delivery_mode: "video",
      payload: { page: "intervention-video" },
    },
  });
  const playerShellRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const backgroundAudioRef = useRef<HTMLAudioElement | null>(null);
  const lastNonZeroVolumeRef = useRef(1);

  const [activeProgram, setActiveProgram] = useState<InterventionVideoProgram | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isControlPanelOpen, setIsControlPanelOpen] = useState(false);
  const [isVideoReady, setIsVideoReady] = useState(false);
  const [isSeeking, setIsSeeking] = useState(false);
  const [playbackError, setPlaybackError] = useState("");
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [seekValue, setSeekValue] = useState(0);
  const [volume, setVolume] = useState(1);

  useEffect(() => {
    const handleFullscreenChange = () => {
      const fullscreenDocument = document as FullscreenDocument;
      const fullscreenTarget = document.fullscreenElement ?? fullscreenDocument.webkitFullscreenElement ?? null;
      setIsFullscreen(fullscreenTarget === playerShellRef.current);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange as EventListener);

    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("webkitfullscreenchange", handleFullscreenChange as EventListener);
      videoRef.current?.pause();
      backgroundAudioRef.current?.pause();
    };
  }, []);

  const handleReturnToLanding = useEffectEvent((reason: "return_button") => {
    void trackEvent({
      event_type: "experience_exited",
      program_id: activeProgram?.id ?? "video-regulation",
      program_title: activeProgram?.title ?? COPY.pageTitle,
      delivery_mode: "video",
      payload: {
        page: "intervention-video",
        reason,
        destination: "intervention-landing",
        active_program_id: activeProgram?.id ?? null,
        active_program_title: activeProgram?.title ?? null,
        current_time_seconds: Number(currentTime.toFixed(1)),
        duration_seconds: Number(duration.toFixed(1)),
      },
    });

    navigate(APP_PATHS.intervention, {
      state: buildRouteState(),
    });
  });

  const syncAndPlay = async (
    program: InterventionVideoProgram,
    options: { restart: boolean },
  ) => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    const videoSrc = toAssetUri(program.videoSrc);
    const backgroundAudio = backgroundAudioRef.current;
    const backgroundMusicSrc = program.backgroundMusicSrc ? toAssetUri(program.backgroundMusicSrc) : null;

    if (video.getAttribute("src") !== videoSrc) {
      setIsVideoReady(false);
      video.setAttribute("src", videoSrc);
      video.load();
    }

    if (options.restart) {
      setIsVideoReady(false);
      video.currentTime = 0;
      setCurrentTime(0);
      setSeekValue(0);
    }

    video.volume = volume;
    video.muted = Boolean(backgroundMusicSrc) || volume === 0;
    video.loop = false;

    if (backgroundAudio) {
      backgroundAudio.pause();
      if (backgroundMusicSrc) {
        if (backgroundAudio.getAttribute("src") !== backgroundMusicSrc) {
          backgroundAudio.setAttribute("src", backgroundMusicSrc);
          backgroundAudio.load();
        }
        if (options.restart) {
          backgroundAudio.currentTime = 0;
        }
        backgroundAudio.volume = volume;
        backgroundAudio.muted = volume === 0;
        backgroundAudio.loop = true;
      } else {
        backgroundAudio.loop = false;
      }
    }

    try {
      const videoPlayPromise = video.play();
      const backgroundAudioPlayPromise = backgroundMusicSrc && backgroundAudio
        ? backgroundAudio.play().catch(() => undefined)
        : null;
      await videoPlayPromise;
      await backgroundAudioPlayPromise;
      setIsPlaying(true);
      setPlaybackError("");
    } catch {
      setIsPlaying(false);
      setPlaybackError(COPY.playbackBlocked);
    }
  };

  const handleSelectProgram = async (program: InterventionVideoProgram) => {
    setActiveProgram(program);
    setIsControlPanelOpen(false);
    void trackEvent({
      event_type: "media_selected",
      program_id: program.id,
      program_title: program.title,
      delivery_mode: "video",
      payload: {
        video_src: program.videoSrc,
        poster_src: program.posterSrc,
      },
    });
    await syncAndPlay(program, { restart: true });
  };

  const handleChangeProgram = () => {
    videoRef.current?.pause();
    backgroundAudioRef.current?.pause();
    setIsPlaying(false);
    setIsControlPanelOpen(false);
    setActiveProgram(null);
  };

  const handleTogglePlayback = async () => {
    const video = videoRef.current;
    if (!activeProgram || !video) {
      return;
    }

    if (isPlaying) {
      video.pause();
      backgroundAudioRef.current?.pause();
      setIsPlaying(false);
      return;
    }

    await syncAndPlay(activeProgram, { restart: false });
  };

  const handleReplay = async () => {
    if (!activeProgram) {
      return;
    }

    await syncAndPlay(activeProgram, { restart: true });
  };

  const handleFullscreenToggle = async () => {
    if (!activeProgram) {
      return;
    }

    if (isFullscreen) {
      await exitPlayerFullscreen();
      return;
    }

    await requestPlayerFullscreen(playerShellRef.current).catch(() => {
      setPlaybackError(COPY.cannotReenterFullscreen);
    });
  };

  const handleSeek = (nextValue: number) => {
    setSeekValue(nextValue);
  };

  const commitSeek = () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    const nextValue = Math.min(Math.max(seekValue, 0), duration || 0);
    video.currentTime = nextValue;
    if (activeProgram?.backgroundMusicSrc && backgroundAudioRef.current) {
      backgroundAudioRef.current.currentTime = getLoopedAudioTime(backgroundAudioRef.current, nextValue);
    }
    setCurrentTime(nextValue);
    setSeekValue(nextValue);
  };

  const handleSeekStart = () => {
    setIsSeeking(true);
  };

  const handleSeekEnd = () => {
    commitSeek();
    setIsSeeking(false);
  };

  const handleVolumeChange = (nextVolume: number) => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    video.volume = nextVolume;
    video.muted = Boolean(activeProgram?.backgroundMusicSrc) || nextVolume === 0;
    if (backgroundAudioRef.current) {
      backgroundAudioRef.current.volume = nextVolume;
      backgroundAudioRef.current.muted = nextVolume === 0;
    }
    setVolume(nextVolume);

    if (nextVolume > 0) {
      lastNonZeroVolumeRef.current = nextVolume;
    }
  };

  const handleToggleMute = () => {
    if (volume === 0) {
      handleVolumeChange(lastNonZeroVolumeRef.current || 1);
      return;
    }

    handleVolumeChange(0);
  };

  const handleVideoLoadedMetadata = () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    setDuration(Number.isFinite(video.duration) ? video.duration : 0);
  };

  const handleVideoTimeUpdate = () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    if (isSeeking) {
      return;
    }

    if (activeProgram?.backgroundMusicSrc && backgroundAudioRef.current) {
      const backgroundAudio = backgroundAudioRef.current;
      const expectedAudioTime = getLoopedAudioTime(backgroundAudio, video.currentTime);
      if (Math.abs(backgroundAudio.currentTime - expectedAudioTime) > 0.35) {
        backgroundAudio.currentTime = expectedAudioTime;
      }
    }

    setCurrentTime(video.currentTime);
    setSeekValue(video.currentTime);
  };

  const handleVideoEnded = () => {
    backgroundAudioRef.current?.pause();
    setCurrentTime(duration);
    setSeekValue(duration);
    setIsPlaying(false);
  };

  return (
    <ConsultationLayout backgroundImage="/intervention/video/theater-background.png" title={COPY.pageTitle}>
      <div className="relative h-full w-full overflow-hidden bg-black/20">
        <div
          className={
            activeProgram
              ? "absolute inset-0"
              : "absolute inset-x-[20.5%] bottom-[24.5%] top-[2%] flex min-h-0 overflow-hidden rounded-md border border-black/55 bg-black/48 shadow-[0_18px_50px_rgba(0,0,0,0.48)] backdrop-blur-[2px]"
          }
        >
          <section
            className={`flex min-h-0 min-w-0 flex-1 flex-col p-4 text-white md:p-5 ${
              activeProgram ? "overflow-visible" : "overflow-hidden border-r border-white/12"
            }`}
          >
            <div className={activeProgram ? "hidden" : "flex items-center justify-between gap-3"}>
              <div>
                <p className="text-xs uppercase tracking-[0.35em] text-cyan-200/70">Video Regulation</p>
                <h1 className="mt-3 text-2xl font-semibold tracking-[0.08em] text-white md:text-3xl">{COPY.heroTitle}</h1>
              </div>
              <button
                type="button"
                onClick={() => handleReturnToLanding("return_button")}
                className="rounded-full border border-white/20 bg-white/8 px-4 py-2 text-sm text-white/85 transition hover:bg-white/14"
              >
                {COPY.backHome}
              </button>
            </div>
            {!activeProgram && sessionError ? <p className="mt-3 text-sm text-amber-200/90">{sessionError}</p> : null}

            {/*
              The artwork is rendered with object-cover. These measurements map the
              theater screen and its lower black apron in the 1672 × 941 source
              image, so the playback view leaves a narrow black stage edge before
              the seats.
            */}
            <div
              ref={playerShellRef}
              className={`overflow-hidden bg-black/60 ${
                activeProgram
                  ? "fixed left-1/2 top-[calc(50vh_-_max(19.65vw,34.91vh))] z-20 h-[calc(max(33.31vw,59.19vh)_-_20px)] w-[max(58.37vw,103.72vh)] -translate-x-1/2 rounded-none border-0"
                  : "relative mt-5 flex-1 rounded-[28px] border border-white/10"
              }`}
            >
              <audio ref={backgroundAudioRef} preload="auto" />
              <video
                ref={videoRef}
                className="h-full w-full object-cover"
                playsInline
                controls={false}
                poster={activeProgram ? toAssetUri(activeProgram.posterSrc) : "/cover-background-v2.png"}
                preload="metadata"
                onLoadedMetadata={handleVideoLoadedMetadata}
                onLoadedData={() => setIsVideoReady(true)}
                onCanPlay={() => setIsVideoReady(true)}
                onTimeUpdate={handleVideoTimeUpdate}
                onEnded={handleVideoEnded}
                onPause={() => {
                  backgroundAudioRef.current?.pause();
                  setIsPlaying(false);
                }}
                onPlay={() => {
                  setIsPlaying(true);
                  setIsVideoReady(true);
                }}
              />

              {activeProgram ? (
                <>
                  <img
                    src={toAssetUri(activeProgram.posterSrc)}
                    alt={activeProgram.title}
                    className={`pointer-events-none absolute inset-0 h-full w-full object-cover transition-opacity duration-300 ${
                      isVideoReady ? "opacity-0" : "opacity-100"
                    }`}
                  />
                  <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-black/16" />

                  <div className="absolute left-4 top-4 z-10">
                    <button
                      type="button"
                      onClick={handleChangeProgram}
                      className="rounded-full border border-white/12 bg-black/48 px-4 py-2 text-sm text-white shadow-[0_10px_24px_rgba(2,6,23,0.35)] backdrop-blur-xl transition hover:bg-black/62"
                    >
                      {COPY.changeProgram}
                    </button>
                  </div>

                  <div className="absolute right-4 top-4 z-10 flex items-center gap-2" onClick={(event) => event.stopPropagation()}>
                    <button
                      type="button"
                      aria-label={isPlaying ? COPY.pause : COPY.resume}
                      onClick={() => void handleTogglePlayback()}
                      className="flex h-11 w-11 items-center justify-center rounded-full border border-white/12 bg-black/48 text-white shadow-[0_10px_24px_rgba(2,6,23,0.35)] backdrop-blur-xl transition hover:bg-black/62"
                    >
                      {isPlaying ? <Pause size={18} /> : <Play size={18} className="translate-x-[1px]" />}
                    </button>

                    <button
                      type="button"
                      aria-label={COPY.replay}
                      onClick={() => void handleReplay()}
                      className="flex h-11 w-11 items-center justify-center rounded-full border border-white/12 bg-black/48 text-white shadow-[0_10px_24px_rgba(2,6,23,0.35)] backdrop-blur-xl transition hover:bg-black/62"
                    >
                      <RotateCcw size={18} />
                    </button>

                    <button
                      type="button"
                      aria-label={volume === 0 ? COPY.restoreVolume : COPY.mute}
                      onClick={handleToggleMute}
                      className="flex h-11 w-11 items-center justify-center rounded-full border border-white/12 bg-black/48 text-white shadow-[0_10px_24px_rgba(2,6,23,0.35)] backdrop-blur-xl transition hover:bg-black/62"
                    >
                      {volume === 0 ? <VolumeX size={18} /> : <Volume2 size={18} />}
                    </button>

                    <button
                      type="button"
                      aria-label={isFullscreen ? COPY.exitFullscreen : COPY.enterFullscreen}
                      onClick={() => void handleFullscreenToggle()}
                      className="flex h-11 w-11 items-center justify-center rounded-full border border-white/12 bg-black/48 text-white shadow-[0_10px_24px_rgba(2,6,23,0.35)] backdrop-blur-xl transition hover:bg-black/62"
                    >
                      {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
                    </button>

                    <button
                      type="button"
                      aria-label={isControlPanelOpen ? COPY.controlPanelClose : COPY.controlPanelOpen}
                      onClick={() => setIsControlPanelOpen((current) => !current)}
                      className="flex h-11 w-11 items-center justify-center rounded-full border border-white/12 bg-black/48 text-white shadow-[0_10px_24px_rgba(2,6,23,0.35)] backdrop-blur-xl transition hover:bg-black/62"
                    >
                      <SlidersHorizontal size={18} />
                    </button>
                  </div>

                  {isControlPanelOpen ? (
                    <div
                      className="absolute right-4 top-[4.75rem] z-10 w-[min(320px,calc(100%-2rem))] rounded-[24px] border border-white/12 bg-black/62 p-4 text-white shadow-[0_20px_50px_rgba(2,6,23,0.42)] backdrop-blur-2xl"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <div className="flex items-center justify-between text-xs uppercase tracking-[0.24em] text-white/55">
                        <span>{COPY.panelTitle}</span>
                        <span>
                          {formatDuration(currentTime)} / {formatDuration(duration)}
                        </span>
                      </div>

                      <div className="mt-4">
                        <div className="flex items-center justify-between text-sm text-white/72">
                          <span>{COPY.progressLabel}</span>
                          <span>{Math.round(duration ? (currentTime / duration) * 100 : 0)}%</span>
                        </div>
                        <input
                          type="range"
                          min={0}
                          max={duration || 0}
                          step={0.1}
                          value={duration ? Math.min(isSeeking ? seekValue : currentTime, duration) : 0}
                          onInput={(event) => handleSeek(Number((event.target as HTMLInputElement).value))}
                          onChange={(event) => handleSeek(Number(event.target.value))}
                          onMouseDown={handleSeekStart}
                          onMouseUp={handleSeekEnd}
                          onTouchStart={handleSeekStart}
                          onTouchEnd={handleSeekEnd}
                          onKeyDown={(event) => {
                            if (event.key.startsWith("Arrow") || event.key === "Home" || event.key === "End") {
                              handleSeekStart();
                            }
                          }}
                          onKeyUp={(event) => {
                            if (event.key.startsWith("Arrow") || event.key === "Home" || event.key === "End") {
                              handleSeekEnd();
                            }
                          }}
                          className="mt-3 h-2 w-full cursor-pointer appearance-none rounded-full bg-white/20 accent-cyan-300"
                        />
                      </div>

                      <div className="mt-5">
                        <div className="flex items-center justify-between text-sm text-white/72">
                          <span>{COPY.volumeLabel}</span>
                          <span>{Math.round(volume * 100)}%</span>
                        </div>
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.01}
                          value={volume}
                          onChange={(event) => handleVolumeChange(Number(event.target.value))}
                          className="mt-3 h-2 w-full cursor-pointer appearance-none rounded-full bg-white/20 accent-cyan-300"
                        />
                      </div>
                    </div>
                  ) : null}
                </>
              ) : null}
            </div>

            <div className={activeProgram ? "hidden" : "mt-3 flex flex-col gap-3 rounded-2xl border border-white/10 bg-black/28 px-4 py-3 text-white/90 md:flex-row md:items-center md:justify-between"}>
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-[0.25em] text-white/45">{COPY.playbackCardLabel}</p>
                <p className="mt-2 truncate text-lg font-medium text-white">{activeProgram?.title ?? COPY.emptyProgram}</p>
                <p className="mt-1 text-sm text-white/60">{activeProgram?.subtitle ?? COPY.emptyHint}</p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => void handleReplay()}
                  disabled={!activeProgram}
                  className="rounded-full border border-white/18 bg-white/8 px-4 py-2 text-sm text-white transition hover:bg-white/14 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {COPY.replay}
                </button>
                <button
                  type="button"
                  onClick={() => setIsControlPanelOpen((current) => !current)}
                  disabled={!activeProgram}
                  className="rounded-full border border-white/18 bg-white/8 px-4 py-2 text-sm text-white transition hover:bg-white/14 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isControlPanelOpen ? COPY.moreControlsClose : COPY.moreControlsOpen}
                </button>
                <button
                  type="button"
                  onClick={() => void handleFullscreenToggle()}
                  disabled={!activeProgram}
                  className="rounded-full border border-white/18 bg-white/8 px-4 py-2 text-sm text-white transition hover:bg-white/14 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isFullscreen ? COPY.exitFullscreen : COPY.enterFullscreen}
                </button>
              </div>
            </div>

            {!activeProgram && playbackError ? (
              <div className="mt-4 rounded-2xl border border-amber-300/25 bg-amber-100/10 px-4 py-3 text-sm text-amber-100">
                {playbackError}
              </div>
            ) : null}
          </section>

          <aside className={activeProgram ? "hidden" : "flex w-[38%] min-w-[230px] flex-col overflow-y-auto bg-black/32 p-4 text-white backdrop-blur-sm md:p-5"}>
            <p className="text-xs uppercase tracking-[0.28em] text-cyan-100/75">Program Selection</p>
            <h2 className="mt-2 text-xl font-semibold tracking-[0.06em] text-white">{COPY.selectionTitle}</h2>
            <p className="mt-2 text-sm leading-5 text-white/75">选择一段画面，开始影院体验。</p>

            <div className="mt-4 flex flex-col gap-2.5">
              {INTERVENTION_VIDEO_PROGRAMS.map((program) => {
                const isActive = activeProgram?.id === program.id;

                return (
                  <button
                    key={program.id}
                    type="button"
                    onClick={() => void handleSelectProgram(program)}
                    className={`rounded-2xl border px-4 py-3 text-left transition ${
                      isActive
                        ? "border-amber-200/80 bg-amber-100/22 text-white shadow-[0_10px_26px_rgba(245,158,11,0.18)]"
                        : "border-white/18 bg-black/38 text-white/92 hover:border-amber-100/55 hover:bg-white/12"
                    }`}
                  >
                    <p className="text-base font-semibold tracking-[0.08em]">{program.title}</p>
                    <p className="mt-1 text-sm leading-5 text-white/72">{program.subtitle}</p>
                  </button>
                );
              })}
            </div>
          </aside>
        </div>
      </div>
    </ConsultationLayout>
  );
}
