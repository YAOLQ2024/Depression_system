import { useEffect, useMemo, useRef, useState } from "react";
import { PauseCircle, PlayCircle, SkipBack, SkipForward } from "lucide-react";

import { ConsultationLayout } from "../layouts";
import {
  SeamlessVideoPlayer,
  type SeamlessVideoClip,
  type SeamlessVideoPlayerHandle,
  type SeamlessVideoPlayerState,
} from "../components/video";
import {
  createVideoNodeTransitionAdapter,
  useVideoNodeTransitionController,
  type VideoNode,
} from "../features/video-node";

type DemoTransitionResult = {
  nextIndex: number;
  nextNode: VideoNode;
};

const DEMO_CLIPS: SeamlessVideoClip[] = [
  {
    clipKey: "consultation:greeting-001",
    src: "/digital-human/consultation-v1/greeting-001.webm",
    label: "咨询问候",
  },
  {
    clipKey: "consultation:chief-complaint-001",
    src: "/digital-human/consultation-v1/chief-complaint-001.webm",
    label: "主诉 001",
  },
  {
    clipKey: "assessment:phq9-001",
    src: "/digital-human/scale-assessment-v1/phq9-001.webm",
    label: "PHQ-9 第 1 题",
  },
];

function getWrappedClip(index: number) {
  const normalized = ((index % DEMO_CLIPS.length) + DEMO_CLIPS.length) % DEMO_CLIPS.length;
  return DEMO_CLIPS[normalized];
}

function getWrappedVideoNode(index: number): VideoNode {
  const clip = getWrappedClip(index);
  const isConsultation = clip.clipKey.startsWith("consultation:");

  return {
    nodeKey: clip.clipKey,
    questionKey: clip.clipKey,
    sessionKind: isConsultation ? "consultation" : "assessment",
    source: isConsultation ? "consultation_system_question" : "assessment_question",
    transitionMode: "auto_commit",
    stageId: isConsultation ? "demo-consultation" : "demo-assessment",
    stageLabel: isConsultation ? "咨询 Demo" : "量表 Demo",
    stageOrder: isConsultation ? 1 : 2,
    videoAssetId: clip.clipKey,
    videoUri: clip.src,
    displayText: clip.label || clip.clipKey,
    subtitleText: clip.label || clip.clipKey,
    responseRequired: false,
  };
}

function formatLayerStatus(state: SeamlessVideoPlayerState | null, layerId: "A" | "B") {
  const layer = state?.layers[layerId];
  if (!layer) {
    return "未初始化";
  }

  const clipKey = layer.clipKey || "empty";
  return `${clipKey} · ${layer.phase}${layer.isReady ? " · ready" : ""}${layer.isActive ? " · active" : ""}`;
}

function formatNodeStatus(node: VideoNode | null) {
  if (!node) {
    return "null";
  }

  return `${node.nodeKey} · ${node.transitionMode} · ${node.stageLabel || "unknown-stage"}`;
}

export default function SeamlessVideoPlayerDemoPage() {
  const playerRef = useRef<SeamlessVideoPlayerHandle | null>(null);
  const playerInstanceIdRef = useRef(`svp-${Math.random().toString(36).slice(2, 8)}`);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [playerState, setPlayerState] = useState<SeamlessVideoPlayerState | null>(null);
  const [displayedClipKey, setDisplayedClipKey] = useState<string | null>(null);
  const [lastReadyClipKey, setLastReadyClipKey] = useState<string | null>(null);
  const [playbackBlocked, setPlaybackBlocked] = useState(false);
  const [advanceOnEnd, setAdvanceOnEnd] = useState(true);

  const currentNode = useMemo(() => getWrappedVideoNode(currentIndex), [currentIndex]);
  const adapter = useMemo(
    () =>
      createVideoNodeTransitionAdapter<DemoTransitionResult, DemoTransitionResult>({
        getCurrentNode: () => currentNode,
        canPreviewNextNode: () => true,
        previewNextNode: async () => {
          const nextIndex = currentIndex + 1;
          return {
            nextIndex,
            nextNode: getWrappedVideoNode(nextIndex),
          };
        },
        commitCurrentNode: async () => {
          const nextIndex = currentIndex + 1;
          return {
            nextIndex,
            nextNode: getWrappedVideoNode(nextIndex),
          };
        },
        deriveNextNodeFromResult: (result) => result.nextNode,
      }),
    [currentIndex, currentNode],
  );
  const controller = useVideoNodeTransitionController({ adapter });
  const {
    state: controllerState,
    currentClip,
    preloadClip,
    requestPreview,
    commitCurrentNode,
    markReadyClip,
    markDisplayedClip,
  } = controller;

  useEffect(() => {
    void requestPreview();
  }, [currentNode.nodeKey, requestPreview]);

  const statusItems = useMemo(
    () => [
      { label: "组件实例", value: playerInstanceIdRef.current },
      { label: "Controller currentNode", value: formatNodeStatus(controllerState.currentNode) },
      { label: "Controller prefetchedNode", value: formatNodeStatus(controllerState.prefetchedNode) },
      { label: "Controller readyNode", value: formatNodeStatus(controllerState.readyNode) },
      { label: "Controller displayedNode", value: formatNodeStatus(controllerState.displayedNode) },
      { label: "pendingPreview", value: String(controllerState.pendingPreview) },
      { label: "pendingCommit", value: String(controllerState.pendingCommit) },
      { label: "transitionReason", value: controllerState.transitionReason || "null" },
      { label: "预热 clip", value: preloadClip?.clipKey || "null" },
      { label: "当前 displayedClip", value: displayedClipKey || "等待首帧 ready" },
      { label: "最近 ready clip", value: lastReadyClipKey || "暂无" },
      { label: "活动层", value: playerState?.activeLayerId || "A" },
      { label: "Layer A", value: formatLayerStatus(playerState, "A") },
      { label: "Layer B", value: formatLayerStatus(playerState, "B") },
    ],
    [controllerState, displayedClipKey, lastReadyClipKey, playerState, preloadClip?.clipKey],
  );

  const goToRelativeClip = (offset: number) => {
    setCurrentIndex((current) => current + offset);
  };

  const advanceToNextNode = async () => {
    const result = await commitCurrentNode();
    if (result) {
      setCurrentIndex(result.nextIndex);
    }
  };

  return (
    <ConsultationLayout backgroundImage="/4K.png" title="Seamless Video Player Demo">
      <div className="flex h-full w-full items-center justify-center px-6 py-8">
        <div className="grid h-full w-full max-w-[1440px] gap-6 lg:grid-cols-[minmax(0,1.2fr)_360px]">
          <div className="relative flex min-h-0 flex-col rounded-[2rem] border border-white/14 bg-slate-950/24 p-6 shadow-[0_30px_90px_rgba(15,23,42,0.32)] backdrop-blur-xl">
            <div className="mb-4 flex items-start justify-between gap-4 text-white">
              <div>
                <p className="text-sm uppercase tracking-[0.28em] text-sky-100/70">Step 3 Demo</p>
                <h1 className="mt-2 text-2xl font-semibold">共享 VideoNode Transition Controller</h1>
                <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-200/82">
                  当前 demo 已改为 `adapter + useVideoNodeTransitionController + SeamlessVideoPlayer` 组合。右侧状态会显示
                  `currentNode / prefetchedNode / readyNode / displayedNode` 与 `pendingPreview / pendingCommit`。
                </p>
              </div>
              <div className="rounded-full border border-emerald-300/30 bg-emerald-400/10 px-4 py-2 text-xs text-emerald-100">
                Controller 已脱离页面业务组件
              </div>
            </div>

            <div className="relative flex min-h-0 flex-1 items-center justify-center overflow-hidden rounded-[1.6rem] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.18),transparent_34%),linear-gradient(180deg,rgba(2,6,23,0.5),rgba(2,6,23,0.78))]">
              <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(148,163,184,0.03),rgba(15,23,42,0.12))]" />
              <div className="relative flex h-full w-full items-end justify-center px-6 pt-8">
                <div className="relative h-[min(78vh,860px)] w-full max-w-[82vw]">
                  <SeamlessVideoPlayer
                    ref={playerRef}
                    currentClip={currentClip}
                    preloadClip={preloadClip}
                    className="h-full w-full"
                    layerClassName="flex items-end justify-center"
                    videoClassName="h-full w-auto max-w-full drop-shadow-[0_28px_60px_rgba(15,23,42,0.28)] -translate-y-8 md:-translate-y-12 scale-[1.05] md:scale-[1.12]"
                    onClipReady={(clip) => {
                      markReadyClip(clip.clipKey);
                      setLastReadyClipKey(clip.clipKey);
                    }}
                    onDisplayedClipChange={(clip) => {
                      markDisplayedClip(clip?.clipKey ?? null);
                      setDisplayedClipKey(clip?.clipKey ?? null);
                    }}
                    onEnded={() => {
                      if (advanceOnEnd) {
                        void advanceToNextNode();
                      }
                    }}
                    onPlaybackBlocked={() => {
                      setPlaybackBlocked(true);
                    }}
                    onPlaybackStarted={() => {
                      setPlaybackBlocked(false);
                    }}
                    onStateChange={setPlayerState}
                  />

                  {playbackBlocked ? (
                    <div className="absolute inset-0 z-20 flex items-center justify-center">
                      <button
                        onClick={() => {
                          void playerRef.current?.playDisplayed().catch(() => undefined);
                        }}
                        className="inline-flex items-center gap-3 rounded-full border border-white/20 bg-white/12 px-5 py-3 text-sm font-medium text-white shadow-lg transition hover:bg-white/18"
                      >
                        <PlayCircle className="h-5 w-5" />
                        点击继续播放当前 demo 视频
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3 text-white">
              <button
                onClick={() => goToRelativeClip(-1)}
                className="inline-flex items-center gap-2 rounded-full border border-white/16 bg-white/8 px-4 py-2 text-sm transition hover:bg-white/14"
              >
                <SkipBack className="h-4 w-4" />
                上一段
              </button>
              <button
                onClick={() => {
                  void advanceToNextNode();
                }}
                className="inline-flex items-center gap-2 rounded-full border border-sky-300/28 bg-sky-400/16 px-4 py-2 text-sm text-sky-50 transition hover:bg-sky-400/22"
              >
                <SkipForward className="h-4 w-4" />
                通过 controller 提交并切到下一段
              </button>
              <button
                onClick={() => {
                  playerRef.current?.pauseDisplayed();
                  setPlaybackBlocked(false);
                }}
                className="inline-flex items-center gap-2 rounded-full border border-white/16 bg-white/8 px-4 py-2 text-sm transition hover:bg-white/14"
              >
                <PauseCircle className="h-4 w-4" />
                暂停当前层
              </button>
              <label className="inline-flex items-center gap-2 rounded-full border border-white/14 bg-white/6 px-4 py-2 text-sm text-slate-100">
                <input
                  checked={advanceOnEnd}
                  onChange={(event) => setAdvanceOnEnd(event.target.checked)}
                  type="checkbox"
                  className="h-4 w-4 rounded border-white/30 bg-transparent"
                />
                播放结束后自动 commit 到下一段
              </label>
            </div>
          </div>

          <aside className="flex min-h-0 flex-col rounded-[2rem] border border-white/14 bg-slate-950/24 p-5 text-white shadow-[0_30px_90px_rgba(15,23,42,0.32)] backdrop-blur-xl">
            <p className="text-sm uppercase tracking-[0.26em] text-sky-100/68">Debug Snapshot</p>
            <div className="mt-4 space-y-3 overflow-y-auto pr-1">
              {statusItems.map((item) => (
                <div
                  key={item.label}
                  className="rounded-[1.2rem] border border-white/10 bg-white/6 px-4 py-3 shadow-[0_12px_30px_rgba(15,23,42,0.14)]"
                >
                  <p className="text-[11px] uppercase tracking-[0.22em] text-slate-300/72">{item.label}</p>
                  <p className="mt-2 break-all text-sm leading-6 text-white/92">{item.value}</p>
                </div>
              ))}
            </div>

            <div className="mt-5 rounded-[1.2rem] border border-amber-300/18 bg-amber-400/10 px-4 py-4 text-sm leading-7 text-amber-50/92">
              <p className="font-medium">验证建议</p>
              <p className="mt-2">
                点击“通过 controller 提交并切到下一段”，应先看到 `pendingCommit` 变化，再看到 `currentNode`、`displayedNode`
                和播放器层状态完成切换，而页面本身不需要直接维护这些节点状态。
              </p>
            </div>
          </aside>
        </div>
      </div>
    </ConsultationLayout>
  );
}
