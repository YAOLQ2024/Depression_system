import type { VideoNode } from "./types";

const LOCAL_CONSULTATION_PREVIEW_NODES: Record<string, VideoNode> = {
  "greeting-001": {
    nodeKey: "ask-chief-complaint-001",
    questionKey: "chief-complaint-001",
    sessionKind: "consultation",
    source: "consultation_question",
    transitionMode: "submit_driven",
    stageId: "stage-02-chief-complaint",
    stageLabel: "主诉采集",
    stageOrder: 2,
    videoAssetId: "chief-complaint-001",
    videoUri: "/digital-human/consultation-v1/chief-complaint-001.webm",
    displayText: "您今天主要是因为什么问题来就诊？",
    subtitleText: "您今天主要是因为什么问题来就诊？",
    responseRequired: true,
  },
};

export function previewLocalConsultationNextNode(currentNode: VideoNode) {
  if (
    currentNode.sessionKind !== "consultation" ||
    currentNode.transitionMode !== "auto_commit" ||
    !currentNode.questionKey
  ) {
    return null;
  }

  // Only deterministic fixed intros use a local preview node. Branch-dependent
  // system prompts still need the backend snapshot to resolve the real next
  // state.
  return LOCAL_CONSULTATION_PREVIEW_NODES[currentNode.questionKey] ?? null;
}
