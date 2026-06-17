import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Maximize2, Minimize2, Pause, Play, Volume2, VolumeX } from "lucide-react";

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

function toAssetUri(path: string) {
  return encodeURI(path);
}

function getLoopedVideoTime(audioTime: number, videoDuration: number) {
  if (!Number.isFinite(videoDuration) || videoDuration <= 0) {
    return 0;
  }

  return audioTime % videoDuration;
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
      program_id: "guided-video",
      program_title: "视频调节",
      delivery_mode: "video",
      payload: { page: "intervention-video" },
    },
  });
  const playerShellRef = useRef<HTMLDivElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const lastNonZeroVolumeRef = useRef(1);

  const [activeProgram, setActiveProgram] = useState<InterventionVideoProgram | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [playbackError, setPlaybackError] = useState("");
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
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
      audioRef.current?.pause();
      videoRef.current?.pause();
    };
  }, []);

  const syncVideoWithAudio = (audioTime: number) => {
    const video = videoRef.current;
    if (!video || !Number.isFinite(video.duration) || video.duration <= 0) {
      return;
    }

    const nextVideoTime = getLoopedVideoTime(audioTime, video.duration);

    if (Math.abs(video.currentTime - nextVideoTime) > 0.35) {
      video.currentTime = nextVideoTime;
    }
  };

  const syncAndPlay = async (
    program: InterventionVideoProgram,
    options: { restart: boolean; enterFullscreen?: boolean },
  ) => {
    const audio = audioRef.current;
    const video = videoRef.current;

    if (!audio || !video) {
      return;
    }

    const audioSrc = toAssetUri(program.audioSrc);
    const videoSrc = toAssetUri(program.videoSrc);

    if (audio.getAttribute("src") !== audioSrc) {
      audio.setAttribute("src", audioSrc);
      audio.load();
    }

    if (video.getAttribute("src") !== videoSrc) {
      video.setAttribute("src", videoSrc);
      video.load();
    }

    if (options.restart) {
      audio.currentTime = 0;
      video.currentTime = 0;
      setCurrentTime(0);
    }

    audio.volume = volume;
    video.muted = true;
    video.loop = true;

    if (options.enterFullscreen) {
      void requestPlayerFullscreen(playerShellRef.current).catch(() => {
        setPlaybackError("未能进入全屏，但视频和音乐已开始播放。");
      });
    }

    try {
      await Promise.all([video.play(), audio.play()]);
      setIsPlaying(true);
      setPlaybackError("");
    } catch {
      setIsPlaying(false);
      setPlaybackError("浏览器拦截了播放，请点击继续按钮重试。");
    }
  };

  const handleSelectProgram = async (program: InterventionVideoProgram) => {
    setActiveProgram(program);
    void trackEvent({
      event_type: "media_selected",
      program_id: program.id,
      program_title: program.title,
      delivery_mode: "video",
      payload: {
        audio_src: program.audioSrc,
        video_src: program.videoSrc,
      },
    });
    await syncAndPlay(program, { restart: true, enterFullscreen: true });
  };

  const handleTogglePlayback = async () => {
    if (!activeProgram) {
      return;
    }

    const audio = audioRef.current;
    const video = videoRef.current;

    if (!audio || !video) {
      return;
    }

    if (isPlaying) {
      audio.pause();
      video.pause();
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
      setPlaybackError("当前浏览器未能再次进入全屏。");
    });
  };

  const handleSeek = (nextValue: number) => {
    const audio = audioRef.current;
    const video = videoRef.current;

    if (!audio || !video) {
      return;
    }

    audio.currentTime = nextValue;
    setCurrentTime(nextValue);

    if (Number.isFinite(video.duration) && video.duration > 0) {
      video.currentTime = getLoopedVideoTime(nextValue, video.duration);
    }
  };

  const handleVolumeChange = (nextVolume: number) => {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    audio.volume = nextVolume;
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

  const handleAudioLoadedMetadata = () => {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    setDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
  };

  const handleAudioTimeUpdate = () => {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    setCurrentTime(audio.currentTime);
    syncVideoWithAudio(audio.currentTime);
  };

  const handleAudioEnded = () => {
    const video = videoRef.current;

    if (video) {
      video.pause();
      video.currentTime = 0;
    }

    setCurrentTime(duration);
    setIsPlaying(false);
  };

  return (
    <ConsultationLayout backgroundImage="/bg.webp" title="视频调节">
      <div className="relative flex h-full w-full overflow-hidden bg-[radial-gradient(circle_at_top,rgba(130,181,255,0.18),transparent_42%),linear-gradient(180deg,rgba(10,16,31,0.18),rgba(10,16,31,0.78))]">
        <div className="mx-auto flex h-full w-full max-w-7xl flex-col gap-6 px-5 pb-6 pt-6 md:px-8 lg:flex-row">
          <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[32px] border border-white/14 bg-slate-950/38 p-4 shadow-[0_24px_60px_rgba(2,6,23,0.45)] backdrop-blur-xl md:p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.35em] text-cyan-200/70">Video Regulation</p>
                <h1 className="mt-3 text-2xl font-semibold tracking-[0.08em] text-white md:text-3xl">看一段视频</h1>
              </div>
              <button
                type="button"
                onClick={() =>
                  navigate(APP_PATHS.intervention, {
                    state: buildRouteState(),
                  })
                }
                className="rounded-full border border-white/20 bg-white/8 px-4 py-2 text-sm text-white/85 transition hover:bg-white/14"
              >
                返回干预首页
              </button>
            </div>
            {sessionError ? <p className="mt-3 text-sm text-amber-200/90">{sessionError}</p> : null}

            <div
              ref={playerShellRef}
              className="relative mt-5 flex-1 overflow-hidden rounded-[28px] border border-white/10 bg-black/30"
            >
              <video
                ref={videoRef}
                className="h-full w-full object-cover"
                playsInline
                controls={false}
                poster="/cover-background-v2.png"
              />

              {activeProgram ? (
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/35 to-transparent px-4 pb-4 pt-12 md:px-6">
                  <div className="mx-auto flex max-w-5xl items-center gap-3 rounded-full border border-white/10 bg-black/40 px-3 py-3 backdrop-blur-xl">
                    <button
                      type="button"
                      aria-label={isPlaying ? "暂停播放" : "继续播放"}
                      onClick={() => void handleTogglePlayback()}
                      className="flex h-11 w-11 items-center justify-center rounded-full bg-cyan-300 text-slate-950 transition hover:bg-cyan-200"
                    >
                      {isPlaying ? <Pause size={20} /> : <Play size={20} className="translate-x-[1px]" />}
                    </button>

                    <div className="flex-1">
                      <input
                        type="range"
                        min={0}
                        max={duration || 0}
                        step={0.1}
                        value={duration ? Math.min(currentTime, duration) : 0}
                        onChange={(event) => handleSeek(Number(event.target.value))}
                        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-white/20 accent-cyan-300"
                      />
                    </div>

                    <button
                      type="button"
                      aria-label={isFullscreen ? "退出全屏" : "进入全屏"}
                      onClick={() => void handleFullscreenToggle()}
                      className="flex h-11 w-11 items-center justify-center rounded-full border border-white/12 bg-white/10 text-white transition hover:bg-white/16"
                    >
                      {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
                    </button>

                    <button
                      type="button"
                      aria-label={volume === 0 ? "恢复音量" : "静音"}
                      onClick={handleToggleMute}
                      className="flex h-11 w-11 items-center justify-center rounded-full border border-white/12 bg-white/10 text-white transition hover:bg-white/16"
                    >
                      {volume === 0 ? <VolumeX size={18} /> : <Volume2 size={18} />}
                    </button>

                    <div className="w-20 sm:w-28">
                      <input
                        type="range"
                        min={0}
                        max={1}
                        step={0.01}
                        value={volume}
                        onChange={(event) => handleVolumeChange(Number(event.target.value))}
                        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-white/20 accent-cyan-300"
                      />
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="mt-5 flex flex-col gap-4 rounded-[28px] border border-white/10 bg-black/18 px-4 py-4 text-white/90 md:flex-row md:items-center md:justify-between md:px-5">
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-[0.25em] text-white/45">当前播放</p>
                <p className="mt-2 truncate text-lg font-medium text-white">
                  {activeProgram?.title ?? "请选择一首曲目开始播放"}
                </p>
                <p className="mt-1 text-sm text-white/60">
                  {activeProgram?.subtitle ?? "选择音乐后将直接进入全屏播放。"}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => void handleReplay()}
                  disabled={!activeProgram}
                  className="rounded-full border border-white/18 bg-white/8 px-4 py-2 text-sm text-white transition hover:bg-white/14 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  从头播放
                </button>
                <button
                  type="button"
                  onClick={() => void handleFullscreenToggle()}
                  disabled={!activeProgram}
                  className="rounded-full border border-white/18 bg-white/8 px-4 py-2 text-sm text-white transition hover:bg-white/14 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isFullscreen ? "退出全屏" : "进入全屏"}
                </button>
              </div>
            </div>

            {playbackError ? (
              <div className="mt-4 rounded-2xl border border-amber-300/25 bg-amber-100/10 px-4 py-3 text-sm text-amber-100">
                {playbackError}
              </div>
            ) : null}
          </section>

          <aside className="w-full rounded-[32px] border border-white/14 bg-white/8 p-5 shadow-[0_20px_50px_rgba(2,6,23,0.35)] backdrop-blur-xl lg:w-[380px]">
            <p className="text-xs uppercase tracking-[0.35em] text-cyan-100/65">Program Selection</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-[0.06em] text-white">选择一段音乐</h2>
            <p className="mt-3 text-sm leading-6 text-white/68">
              点击任一选项后，会直接进入全屏播放，你也可以随时调节音量、进度并重新进入全屏。
            </p>

            <div className="mt-6 flex flex-col gap-3">
              {INTERVENTION_VIDEO_PROGRAMS.map((program) => {
                const isActive = activeProgram?.id === program.id;

                return (
                  <button
                    key={program.id}
                    type="button"
                    onClick={() => void handleSelectProgram(program)}
                    className={`rounded-[24px] border px-4 py-4 text-left transition ${
                      isActive
                        ? "border-cyan-300/70 bg-cyan-300/18 text-white shadow-[0_12px_32px_rgba(45,212,191,0.15)]"
                        : "border-white/12 bg-slate-950/26 text-white/88 hover:border-white/28 hover:bg-white/10"
                    }`}
                  >
                    <p className="text-base font-medium tracking-[0.02em]">{program.title}</p>
                    <p className="mt-2 text-sm leading-6 text-white/62">{program.subtitle}</p>
                  </button>
                );
              })}
            </div>
          </aside>
        </div>

        <audio
          ref={audioRef}
          onLoadedMetadata={handleAudioLoadedMetadata}
          onTimeUpdate={handleAudioTimeUpdate}
          onEnded={handleAudioEnded}
          preload="metadata"
        />
      </div>
    </ConsultationLayout>
  );
}
