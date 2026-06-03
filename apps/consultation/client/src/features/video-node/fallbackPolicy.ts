import type { VideoNode } from "./types";

export type MissingVideoNodeFallbackBehavior =
  | "none"
  | "manual_commit"
  | "local_skip"
  | "allow_response";

export type MissingVideoNodeFallback = {
  isMissingVideo: boolean;
  behavior: MissingVideoNodeFallbackBehavior;
  title: string;
  description: string;
  actionLabel: string | null;
};

const DEFAULT_MISSING_VIDEO_FALLBACK: MissingVideoNodeFallback = {
  isMissingVideo: false,
  behavior: "none",
  title: "",
  description: "",
  actionLabel: null,
};

export function resolveMissingVideoNodeFallback(node: VideoNode | null): MissingVideoNodeFallback {
  if (!node || node.videoUri) {
    return DEFAULT_MISSING_VIDEO_FALLBACK;
  }

  if (node.transitionMode === "local_only") {
    return {
      isMissingVideo: true,
      behavior: "local_skip",
      title: "当前引导视频尚未接入",
      description: "已按统一回退规则跳过当前引导，直接进入本阶段下一视频节点。",
      actionLabel: null,
    };
  }

  if (node.responseRequired || node.transitionMode === "submit_driven") {
    return {
      isMissingVideo: true,
      behavior: "allow_response",
      title: "当前题目的视频资源尚未接入",
      description: "已按统一回退规则降级为文字题，本轮仍可直接作答，不阻断业务推进。",
      actionLabel: null,
    };
  }

  return {
    isMissingVideo: true,
    behavior: "manual_commit",
    title: "当前系统提示视频尚未接入",
    description: "已按统一回退规则保留业务推进能力，可直接继续到下一题，不等待视频补齐。",
    actionLabel: "继续到下一题",
  };
}
