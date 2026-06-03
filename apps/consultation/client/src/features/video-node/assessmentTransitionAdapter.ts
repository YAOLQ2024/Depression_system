import type { AssessmentSession } from "../../types";
import { createVideoNodeTransitionAdapter } from "./adapterFactory";
import type { VideoNode } from "./types";

type AssessmentSubmitResult = AssessmentSession | { assessment_session: AssessmentSession } | VideoNode;

function isVideoNodeLike(candidate: unknown): candidate is VideoNode {
  return Boolean(
    candidate &&
      typeof candidate === "object" &&
      "nodeKey" in candidate &&
      "transitionMode" in candidate &&
      "sessionKind" in candidate,
  );
}

function extractAssessmentSession(result: AssessmentSubmitResult | null) {
  if (!result || isVideoNodeLike(result)) {
    return null;
  }

  if ("assessment_session" in result) {
    return result.assessment_session;
  }

  return result;
}

export function createAssessmentVideoNodeTransitionAdapter({
  currentNode,
  previewLocalNextNode,
  commitCurrentNode,
  deriveNextNodeFromAssessmentSession,
}: {
  currentNode: VideoNode | null;
  previewLocalNextNode?: (currentNode: VideoNode) => VideoNode | null;
  commitCurrentNode?: (currentNode: VideoNode) => Promise<AssessmentSubmitResult | null>;
  deriveNextNodeFromAssessmentSession: (assessmentSession: AssessmentSession) => VideoNode | null;
}) {
  return createVideoNodeTransitionAdapter<AssessmentSubmitResult, AssessmentSubmitResult>({
    getCurrentNode: () => currentNode,
    canPreviewNextNode: (videoNode) =>
      videoNode.transitionMode === "local_only" && Boolean(previewLocalNextNode),
    previewNextNode: async (videoNode) => {
      if (videoNode.transitionMode !== "local_only") {
        return null;
      }

      return previewLocalNextNode?.(videoNode) ?? null;
    },
    commitCurrentNode: async (videoNode) => {
      if (videoNode.transitionMode === "local_only") {
        return previewLocalNextNode?.(videoNode) ?? null;
      }

      return commitCurrentNode?.(videoNode) ?? null;
    },
    deriveNextNodeFromResult: (result) => {
      if (isVideoNodeLike(result)) {
        return result;
      }

      const assessmentSession = extractAssessmentSession(result);
      return assessmentSession ? deriveNextNodeFromAssessmentSession(assessmentSession) : null;
    },
  });
}

