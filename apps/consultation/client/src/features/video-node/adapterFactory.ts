import type { VideoNode, VideoNodeTransitionAdapter } from "./types";

export type CreateVideoNodeTransitionAdapterOptions<TPreviewResult = unknown, TCommitResult = unknown> = {
  getCurrentNode: () => VideoNode | null;
  canPreviewNextNode?: (currentNode: VideoNode) => boolean;
  previewNextNode?: (currentNode: VideoNode) => Promise<TPreviewResult | null>;
  commitCurrentNode?: (currentNode: VideoNode) => Promise<TCommitResult | null>;
  deriveNextNodeFromResult?: (result: TPreviewResult | TCommitResult) => VideoNode | null;
};

export function createVideoNodeTransitionAdapter<TPreviewResult = unknown, TCommitResult = unknown>({
  getCurrentNode,
  canPreviewNextNode,
  previewNextNode,
  commitCurrentNode,
  deriveNextNodeFromResult,
}: CreateVideoNodeTransitionAdapterOptions<TPreviewResult, TCommitResult>): VideoNodeTransitionAdapter<
  TPreviewResult,
  TCommitResult
> {
  return {
    getCurrentNode,
    canPreviewNextNode: (currentNode) => canPreviewNextNode?.(currentNode) ?? false,
    previewNextNode: async (currentNode) => {
      if (!previewNextNode) {
        return null;
      }
      return previewNextNode(currentNode);
    },
    commitCurrentNode: async (currentNode) => {
      if (!commitCurrentNode) {
        return null;
      }
      return commitCurrentNode(currentNode);
    },
    deriveNextNodeFromSubmitResult: (result) => deriveNextNodeFromResult?.(result) ?? null,
  };
}

