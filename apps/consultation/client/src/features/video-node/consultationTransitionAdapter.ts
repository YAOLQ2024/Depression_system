import type { ConsultationAppStore } from "../../app/useConsultationApp";
import type { ConsultationSession } from "../../types";
import { createVideoNodeTransitionAdapter } from "./adapterFactory";
import { previewLocalConsultationNextNode } from "./consultationPreviewNode";
import { buildConsultationCurrentVideoNode } from "./consultationVideoNode";
import type { VideoNode } from "./types";

type ConsultationTransitionActions = Pick<
  ConsultationAppStore["actions"],
  "completeConsultationSystemQuestionItem" | "prefetchConsultationSystemQuestionItem"
>;

type ConsultationTransitionResult = ConsultationSession | VideoNode;

function isVideoNodeLike(candidate: unknown): candidate is VideoNode {
  return Boolean(
    candidate &&
      typeof candidate === "object" &&
      "nodeKey" in candidate &&
      "transitionMode" in candidate &&
      "sessionKind" in candidate,
  );
}

export function createConsultationVideoNodeTransitionAdapter({
  consultation,
  actions,
}: {
  consultation: ConsultationSession | null;
  actions: ConsultationTransitionActions;
}) {
  return createVideoNodeTransitionAdapter<ConsultationTransitionResult, ConsultationTransitionResult>({
    getCurrentNode: () => buildConsultationCurrentVideoNode(consultation),
    canPreviewNextNode: (currentNode) =>
      currentNode.transitionMode === "auto_commit" && Boolean(currentNode.questionKey),
    previewNextNode: async (currentNode) => {
      if (!currentNode.questionKey) {
        return null;
      }

      const localNextNode = previewLocalConsultationNextNode(currentNode);
      if (localNextNode) {
        return localNextNode;
      }

      return actions.prefetchConsultationSystemQuestionItem(currentNode.questionKey);
    },
    commitCurrentNode: async (currentNode) => {
      if (!currentNode.questionKey || currentNode.transitionMode !== "auto_commit" || currentNode.responseRequired) {
        return null;
      }

      return actions.completeConsultationSystemQuestionItem(currentNode.questionKey);
    },
    deriveNextNodeFromResult: (result) =>
      isVideoNodeLike(result) ? result : buildConsultationCurrentVideoNode(result),
  });
}
