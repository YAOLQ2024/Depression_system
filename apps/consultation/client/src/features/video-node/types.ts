export type VideoNodeTransitionMode = "auto_commit" | "submit_driven" | "local_only";

export type VideoNodeSource =
  | "consultation_system_question"
  | "consultation_question"
  | "assessment_stage_intro"
  | "assessment_question";

export type VideoNodeSessionKind = "consultation" | "assessment";

export type VideoNode = {
  nodeKey: string;
  questionKey: string | null;
  sessionKind: VideoNodeSessionKind;
  source: VideoNodeSource;
  transitionMode: VideoNodeTransitionMode;
  stageId: string | null;
  stageLabel: string | null;
  stageOrder: number | null;
  videoAssetId: string | null;
  videoUri: string | null;
  displayText: string;
  subtitleText: string;
  responseRequired: boolean;
};

export const VIDEO_NODE_SHARED_BOUNDARY = {
  player: "SeamlessVideoPlayer",
  controller: "useVideoNodeTransitionController",
} as const;

// Step 1 keeps the player/controller boundary explicit so later work lands in
// shared VideoNode infrastructure instead of new page-private video logic.
export interface VideoNodeTransitionAdapter<TPreviewResult = unknown, TCommitResult = unknown> {
  getCurrentNode(): VideoNode | null;
  canPreviewNextNode(currentNode: VideoNode): boolean;
  previewNextNode(currentNode: VideoNode): Promise<TPreviewResult | null>;
  commitCurrentNode(currentNode: VideoNode): Promise<TCommitResult | null>;
  deriveNextNodeFromSubmitResult(result: TPreviewResult | TCommitResult): VideoNode | null;
}

export function normalizeVideoNodeUri(candidate?: string | null) {
  const normalized = candidate?.trim() ?? "";
  if (!normalized || normalized.toUpperCase() === "TBD") {
    return null;
  }

  return normalized;
}

