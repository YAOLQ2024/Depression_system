import type { ConsultationAppStore } from "../../app/useConsultationApp";
import type { ConsultationSession } from "../../types";
import { createVideoNodeTransitionAdapter } from "./adapterFactory";
import { buildConsultationCurrentVideoNode } from "./consultationVideoNode";

type ConsultationTransitionActions = Pick<
  ConsultationAppStore["actions"],
  "completeConsultationSystemQuestionItem" | "prefetchConsultationSystemQuestionItem"
>;

export function createConsultationVideoNodeTransitionAdapter({
  consultation,
  actions,
}: {
  consultation: ConsultationSession | null;
  actions: ConsultationTransitionActions;
}) {
  return createVideoNodeTransitionAdapter<ConsultationSession, ConsultationSession>({
    getCurrentNode: () => buildConsultationCurrentVideoNode(consultation),
    canPreviewNextNode: (currentNode) =>
      currentNode.transitionMode === "auto_commit" && Boolean(currentNode.questionKey),
    previewNextNode: async (currentNode) => {
      if (!currentNode.questionKey) {
        return null;
      }

      return actions.prefetchConsultationSystemQuestionItem(currentNode.questionKey);
    },
    commitCurrentNode: async (currentNode) => {
      if (!currentNode.questionKey || currentNode.transitionMode !== "auto_commit" || currentNode.responseRequired) {
        return null;
      }

      return actions.completeConsultationSystemQuestionItem(currentNode.questionKey);
    },
    deriveNextNodeFromResult: (result) => buildConsultationCurrentVideoNode(result),
  });
}
