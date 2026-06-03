import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import { buildClipFromVideoNode } from "./clipMapping";
import {
  buildVideoNodeSignature,
  createInitialVideoNodeTransitionState,
  discardPrefetchedVideoNode,
  finalizeCommit,
  markCommitFailed,
  markCommitRequested,
  markDisplayedVideoNode,
  markPreviewFailed,
  markPreviewRequested,
  markVideoNodeReady,
  promotePrefetchedVideoNode,
  resetVideoNodeTransitionState,
  setPrefetchedVideoNode,
  syncCurrentVideoNode,
  type VideoNodeTransitionReason,
  type VideoNodeTransitionState,
} from "./controllerMachine";
import type { VideoNode, VideoNodeTransitionAdapter } from "./types";

function toErrorMessage(caught: unknown) {
  return caught instanceof Error ? caught.message : "视频节点切换失败";
}

export type UseVideoNodeTransitionControllerOptions<TPreviewResult = unknown, TCommitResult = unknown> = {
  adapter: VideoNodeTransitionAdapter<TPreviewResult, TCommitResult>;
};

export type VideoNodeClipLoadScope = "current" | "prefetched" | "unknown";

export function useVideoNodeTransitionController<TPreviewResult = unknown, TCommitResult = unknown>({
  adapter,
}: UseVideoNodeTransitionControllerOptions<TPreviewResult, TCommitResult>) {
  const externalCurrentNode = adapter.getCurrentNode();
  const externalCurrentNodeSignature = buildVideoNodeSignature(externalCurrentNode);

  const [state, setState] = useState<VideoNodeTransitionState>(() =>
    createInitialVideoNodeTransitionState(externalCurrentNode),
  );

  const stateRef = useRef(state);
  const previewRequestIdRef = useRef(0);
  const commitRequestIdRef = useRef(0);
  const previewPromiseRef = useRef<Promise<VideoNode | null> | null>(null);
  const commitPromiseRef = useRef<Promise<TCommitResult | null> | null>(null);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    setState((currentState) =>
      syncCurrentVideoNode(currentState, externalCurrentNode, currentState.currentNode ? "external_current_node" : "initial_sync"),
    );
  }, [externalCurrentNodeSignature]);

  const requestPreview = useEffectEvent(async () => {
    const currentNode = stateRef.current.currentNode;
    const hasPrefetchedNextNode =
      stateRef.current.prefetchedNode?.nodeKey &&
      stateRef.current.prefetchedNode.nodeKey !== currentNode?.nodeKey;
    if (!currentNode || !adapter.canPreviewNextNode(currentNode)) {
      return null;
    }
    if (hasPrefetchedNextNode) {
      return stateRef.current.prefetchedNode;
    }
    if (stateRef.current.pendingPreview && previewPromiseRef.current) {
      return previewPromiseRef.current;
    }
    if (
      stateRef.current.pendingPreview ||
      hasPrefetchedNextNode
    ) {
      return null;
    }

    const expectedNodeKey = currentNode.nodeKey;
    const requestId = previewRequestIdRef.current + 1;
    previewRequestIdRef.current = requestId;
    setState((currentState) => markPreviewRequested(currentState, "preview_requested"));

    const previewPromise = (async () => {
      try {
        const result = await adapter.previewNextNode(currentNode);
        if (previewRequestIdRef.current !== requestId) {
          return null;
        }
        if (stateRef.current.currentNode?.nodeKey !== expectedNodeKey) {
          return null;
        }

        const nextNode = result ? adapter.deriveNextNodeFromSubmitResult(result) : null;
        setState((currentState) => setPrefetchedVideoNode(currentState, nextNode, "preview_resolved"));
        return nextNode;
      } catch (caught) {
        if (
          previewRequestIdRef.current === requestId &&
          stateRef.current.currentNode?.nodeKey === expectedNodeKey
        ) {
          setState((currentState) => markPreviewFailed(currentState, toErrorMessage(caught), "preview_failed"));
        }
        return null;
      } finally {
        if (previewRequestIdRef.current === requestId) {
          previewPromiseRef.current = null;
        }
      }
    })();

    previewPromiseRef.current = previewPromise;
    return previewPromise;
  });

  const commitCurrentNode = useEffectEvent(async () => {
    const currentNode = stateRef.current.currentNode;
    if (!currentNode) {
      return null;
    }
    if (currentNode.transitionMode !== "auto_commit") {
      return null;
    }
    if (commitPromiseRef.current) {
      return commitPromiseRef.current;
    }
    if (stateRef.current.pendingCommit) {
      return null;
    }

    const expectedNodeKey = currentNode.nodeKey;
    const requestId = commitRequestIdRef.current + 1;
    commitRequestIdRef.current = requestId;
    setState((currentState) => markCommitRequested(currentState, "commit_requested"));
    if (
      stateRef.current.prefetchedNode?.nodeKey &&
      stateRef.current.readyNode?.nodeKey === stateRef.current.prefetchedNode.nodeKey
    ) {
      setState((currentState) => promotePrefetchedVideoNode(currentState, "commit_requested"));
    }

    const commitPromise = (async () => {
      try {
        const result = await adapter.commitCurrentNode(currentNode);
        if (commitRequestIdRef.current !== requestId) {
          return null;
        }
        if (stateRef.current.currentNode?.nodeKey !== expectedNodeKey) {
          return result;
        }

        const nextNode = result ? adapter.deriveNextNodeFromSubmitResult(result) : null;
        const transitionReason =
          nextNode &&
          stateRef.current.prefetchedNode?.nodeKey &&
          stateRef.current.prefetchedNode.nodeKey !== nextNode.nodeKey
            ? "commit_mismatch"
            : "commit_resolved";
        setState((currentState) => finalizeCommit(currentState, nextNode, transitionReason));
        return result;
      } catch (caught) {
        if (commitRequestIdRef.current === requestId) {
          setState((currentState) => markCommitFailed(currentState, toErrorMessage(caught), "commit_failed"));
        }
        return null;
      } finally {
        if (commitRequestIdRef.current === requestId) {
          commitPromiseRef.current = null;
        }
      }
    })();

    commitPromiseRef.current = commitPromise;
    return commitPromise;
  });

  const applyResult = useEffectEvent(
    (
      result: TPreviewResult | TCommitResult,
      reason: VideoNodeTransitionReason = "submit_result",
    ) => {
      const nextNode = adapter.deriveNextNodeFromSubmitResult(result);
      setState((currentState) => finalizeCommit(currentState, nextNode, reason));
      return nextNode;
    },
  );

  const primeNextNodeFromResult = useEffectEvent(
    (
      result: TPreviewResult | TCommitResult,
      reason: VideoNodeTransitionReason = "submit_result",
    ) => {
      const nextNode = adapter.deriveNextNodeFromSubmitResult(result);
      setState((currentState) => setPrefetchedVideoNode(currentState, nextNode, reason));
      return nextNode;
    },
  );

  const markReadyClip = useEffectEvent((clipKey: string | null) => {
    setState((currentState) => markVideoNodeReady(currentState, clipKey, "player_ready"));
  });

  const markDisplayedClip = useEffectEvent((clipKey: string | null) => {
    setState((currentState) => markDisplayedVideoNode(currentState, clipKey, "player_displayed"));
  });

  const clearPrefetchedNode = useEffectEvent(() => {
    setState((currentState) => setPrefetchedVideoNode(currentState, null, "manual_reset"));
  });

  const handleClipLoadError = useEffectEvent((clipKey: string | null): VideoNodeClipLoadScope => {
    const currentState = stateRef.current;
    const matchesCurrentNode =
      currentState.currentNode?.nodeKey === clipKey || currentState.displayedNode?.nodeKey === clipKey;
    if (matchesCurrentNode) {
      return "current";
    }

    const matchesPrefetchedNode =
      currentState.prefetchedNode?.nodeKey === clipKey || currentState.readyNode?.nodeKey === clipKey;
    if (matchesPrefetchedNode) {
      setState((nextState) => discardPrefetchedVideoNode(nextState, clipKey, "preload_failed"));
      return "prefetched";
    }

    return "unknown";
  });

  const reset = useEffectEvent(() => {
    setState((currentState) => resetVideoNodeTransitionState(currentState, "manual_reset"));
  });

  const currentClip = useMemo(() => buildClipFromVideoNode(state.currentNode), [state.currentNode]);
  const preloadClip = useMemo(() => {
    if (!state.prefetchedNode || state.prefetchedNode.nodeKey === state.currentNode?.nodeKey) {
      return null;
    }

    return buildClipFromVideoNode(state.prefetchedNode);
  }, [state.currentNode?.nodeKey, state.prefetchedNode]);

  return {
    state,
    currentClip,
    preloadClip,
    requestPreview,
    commitCurrentNode,
    applyResult,
    primeNextNodeFromResult,
    markReadyClip,
    markDisplayedClip,
    clearPrefetchedNode,
    handleClipLoadError,
    reset,
  };
}
