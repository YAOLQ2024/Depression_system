import type { VideoNode } from "./types";

export type VideoNodeTransitionReason =
  | "initial_sync"
  | "external_current_node"
  | "preview_requested"
  | "preview_resolved"
  | "preview_failed"
  | "preload_failed"
  | "commit_requested"
  | "commit_resolved"
  | "commit_mismatch"
  | "commit_failed"
  | "submit_result"
  | "player_ready"
  | "player_displayed"
  | "manual_reset";

export type VideoNodeTransitionState = {
  currentNode: VideoNode | null;
  prefetchedNode: VideoNode | null;
  readyNode: VideoNode | null;
  displayedNode: VideoNode | null;
  pendingPreview: boolean;
  pendingCommit: boolean;
  transitionReason: VideoNodeTransitionReason | null;
  previewError: string | null;
  commitError: string | null;
};

export function buildVideoNodeSignature(node: VideoNode | null | undefined) {
  if (!node) {
    return "";
  }

  return [
    node.sessionKind,
    node.nodeKey,
    node.videoUri || "",
    node.transitionMode,
    node.responseRequired ? "1" : "0",
  ].join("::");
}

export function isSameVideoNode(node: VideoNode | null | undefined, other: VideoNode | null | undefined) {
  return buildVideoNodeSignature(node) === buildVideoNodeSignature(other);
}

function replaceMatchingNode(candidate: VideoNode | null, nextNode: VideoNode | null) {
  if (!candidate || !nextNode) {
    return candidate;
  }

  return candidate.nodeKey === nextNode.nodeKey ? nextNode : candidate;
}

function findNodeByKey(state: VideoNodeTransitionState, nodeKey: string | null) {
  if (!nodeKey) {
    return null;
  }

  for (const candidate of [state.prefetchedNode, state.readyNode, state.currentNode, state.displayedNode]) {
    if (candidate?.nodeKey === nodeKey) {
      return candidate;
    }
  }

  return null;
}

export function createInitialVideoNodeTransitionState(currentNode: VideoNode | null = null): VideoNodeTransitionState {
  return {
    currentNode,
    prefetchedNode: null,
    readyNode: null,
    displayedNode: currentNode,
    pendingPreview: false,
    pendingCommit: false,
    transitionReason: currentNode ? "initial_sync" : null,
    previewError: null,
    commitError: null,
  };
}

export function syncCurrentVideoNode(
  state: VideoNodeTransitionState,
  nextNode: VideoNode | null,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  if (!nextNode) {
    return {
      currentNode: null,
      prefetchedNode: null,
      readyNode: null,
      displayedNode: null,
      pendingPreview: false,
      pendingCommit: false,
      transitionReason: reason,
      previewError: null,
      commitError: null,
    };
  }

  const currentNode = replaceMatchingNode(state.currentNode, nextNode);
  const displayedNode = replaceMatchingNode(state.displayedNode, nextNode);
  const prefetchedNode = replaceMatchingNode(state.prefetchedNode, nextNode);
  const readyNode = replaceMatchingNode(state.readyNode, nextNode);

  if (currentNode?.nodeKey === nextNode.nodeKey) {
    return {
      ...state,
      currentNode: nextNode,
      prefetchedNode,
      readyNode,
      displayedNode,
      pendingPreview: false,
      pendingCommit: false,
      transitionReason: reason,
      previewError: null,
      commitError: null,
    };
  }

  const predictedNextMatches = prefetchedNode?.nodeKey === nextNode.nodeKey;

  return {
    ...state,
    currentNode: nextNode,
    prefetchedNode: predictedNextMatches ? nextNode : null,
    readyNode: predictedNextMatches && readyNode?.nodeKey === nextNode.nodeKey ? nextNode : null,
    displayedNode: displayedNode || nextNode,
    pendingPreview: false,
    pendingCommit: false,
    transitionReason: reason,
    previewError: null,
    commitError: null,
  };
}

export function setPrefetchedVideoNode(
  state: VideoNodeTransitionState,
  nextNode: VideoNode | null,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  return {
    ...state,
    prefetchedNode: nextNode,
    readyNode: nextNode && state.readyNode?.nodeKey === nextNode.nodeKey ? nextNode : null,
    pendingPreview: false,
    transitionReason: reason,
    previewError: null,
  };
}

export function discardPrefetchedVideoNode(
  state: VideoNodeTransitionState,
  nodeKey: string | null,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  const matchesPrefetchedNode = !nodeKey || state.prefetchedNode?.nodeKey === nodeKey;
  const matchesReadyNode = !nodeKey || state.readyNode?.nodeKey === nodeKey;

  if (!matchesPrefetchedNode && !matchesReadyNode) {
    return state;
  }

  return {
    ...state,
    prefetchedNode: matchesPrefetchedNode ? null : state.prefetchedNode,
    readyNode: matchesReadyNode ? null : state.readyNode,
    pendingPreview: false,
    transitionReason: reason,
  };
}

export function markVideoNodeReady(
  state: VideoNodeTransitionState,
  nodeKey: string | null,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  const readyNode = findNodeByKey(state, nodeKey);
  if (!readyNode) {
    return state;
  }

  return {
    ...state,
    readyNode,
    transitionReason: reason,
  };
}

export function markDisplayedVideoNode(
  state: VideoNodeTransitionState,
  nodeKey: string | null,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  const displayedNode = findNodeByKey(state, nodeKey);
  if (!displayedNode) {
    return nodeKey === null
      ? {
          ...state,
          displayedNode: null,
          transitionReason: reason,
        }
      : state;
  }

  return {
    ...state,
    displayedNode,
    prefetchedNode: state.prefetchedNode?.nodeKey === displayedNode.nodeKey ? null : state.prefetchedNode,
    readyNode: state.readyNode?.nodeKey === displayedNode.nodeKey ? null : state.readyNode,
    transitionReason: reason,
  };
}

export function markPreviewRequested(
  state: VideoNodeTransitionState,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  return {
    ...state,
    pendingPreview: true,
    previewError: null,
    transitionReason: reason,
  };
}

export function markPreviewFailed(
  state: VideoNodeTransitionState,
  message: string,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  return {
    ...state,
    pendingPreview: false,
    previewError: message,
    transitionReason: reason,
  };
}

export function markCommitRequested(
  state: VideoNodeTransitionState,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  return {
    ...state,
    pendingCommit: true,
    commitError: null,
    transitionReason: reason,
  };
}

export function promotePrefetchedVideoNode(
  state: VideoNodeTransitionState,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  if (!state.prefetchedNode) {
    return state;
  }

  return {
    ...state,
    currentNode: state.prefetchedNode,
    transitionReason: reason,
  };
}

export function markCommitFailed(
  state: VideoNodeTransitionState,
  message: string,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  return {
    ...state,
    pendingCommit: false,
    commitError: message,
    transitionReason: reason,
  };
}

export function finalizeCommit(
  state: VideoNodeTransitionState,
  nextNode: VideoNode | null,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  const synced = nextNode ? syncCurrentVideoNode(state, nextNode, reason) : state;

  return {
    ...synced,
    pendingCommit: false,
    commitError: null,
    transitionReason: reason,
  };
}

export function resetVideoNodeTransitionState(
  state: VideoNodeTransitionState,
  reason: VideoNodeTransitionReason,
): VideoNodeTransitionState {
  return {
    ...createInitialVideoNodeTransitionState(state.currentNode),
    transitionReason: reason,
  };
}
