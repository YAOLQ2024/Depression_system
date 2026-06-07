import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { INTERVENTION_VIDEO_PROGRAMS, type InterventionVideoProgram } from "../features/intervention/videoPrograms";
import { ConsultationLayout } from "../layouts";
import { APP_PATHS } from "../routes";

function toAssetUri(path: string) {
  return encodeURI(path);
}

export default function InterventionVideoPage() {
  const navigate = useNavigate();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [activeProgram, setActiveProgram] = useState<InterventionVideoProgram | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackError, setPlaybackError] = useState("");

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      videoRef.current?.pause();
    };
  }, []);

  const syncAndPlay = async (program: InterventionVideoProgram, restart: boolean) => {
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

    if (restart) {
      audio.currentTime = 0;
      video.currentTime = 0;
    }

    video.loop = true;
    video.muted = true;

    try {
      await Promise.all([video.play(), audio.play()]);
      setIsPlaying(true);
      setPlaybackError("");
    } catch {
      setIsPlaying(false);
      setPlaybackError("浏览器拦截了自动播放，请点击“继续播放”重试。");
    }
  };

  const handleSelectProgram = async (program: InterventionVideoProgram) => {
    setActiveProgram(program);
    await syncAndPlay(program, true);
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

    await syncAndPlay(activeProgram, false);
  };

  const handleReplay = async () => {
    if (!activeProgram) {
      return;
    }

    await syncAndPlay(activeProgram, true);
  };

  const handleAudioEnded = () => {
    videoRef.current?.pause();

    if (videoRef.current) {
      videoRef.current.currentTime = 0;
    }

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
                <h1 className="mt-3 text-2xl font-semibold tracking-[0.08em] text-white md:text-3xl">
                  看一段视频
                </h1>
              </div>
              <button
                type="button"
                onClick={() => navigate(APP_PATHS.intervention)}
                className="rounded-full border border-white/20 bg-white/8 px-4 py-2 text-sm text-white/85 transition hover:bg-white/14"
              >
                返回干预首页
              </button>
            </div>

            <div className="mt-5 flex-1 overflow-hidden rounded-[28px] border border-white/10 bg-black/30">
              <video
                ref={videoRef}
                className="h-full w-full object-cover"
                playsInline
                controls={false}
                poster="/cover-background-v2.png"
              />
            </div>

            <div className="mt-5 flex flex-col gap-4 rounded-[28px] border border-white/10 bg-black/18 px-4 py-4 text-white/90 md:flex-row md:items-center md:justify-between md:px-5">
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-[0.25em] text-white/45">当前播放</p>
                <p className="mt-2 truncate text-lg font-medium text-white">
                  {activeProgram?.title ?? "请选择一首曲目开始播放"}
                </p>
                <p className="mt-1 text-sm text-white/60">
                  {activeProgram?.subtitle ?? "视频将播放“四景循环无声.mp4”，音乐与视频同步开始。"}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={handleTogglePlayback}
                  disabled={!activeProgram}
                  className="rounded-full bg-cyan-300 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
                >
                  {isPlaying ? "暂停播放" : "继续播放"}
                </button>
                <button
                  type="button"
                  onClick={handleReplay}
                  disabled={!activeProgram}
                  className="rounded-full border border-white/18 bg-white/8 px-4 py-2 text-sm text-white transition hover:bg-white/14 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  从头播放
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
              点击任一选项后，会同时播放对应音乐和同一支静音风景视频。
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

            <div className="mt-6 rounded-[24px] border border-white/10 bg-black/20 px-4 py-4">
              <p className="text-xs uppercase tracking-[0.25em] text-white/42">播放说明</p>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-white/68">
                <li>视频资源：`四景循环无声.mp4`</li>
                <li>音频资源：按当前选择曲目切换</li>
                <li>音乐播放结束时，视频会同步停止</li>
              </ul>
            </div>
          </aside>
        </div>

        <audio ref={audioRef} onEnded={handleAudioEnded} preload="metadata" />
      </div>
    </ConsultationLayout>
  );
}
