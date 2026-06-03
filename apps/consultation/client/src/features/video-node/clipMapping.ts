import type { SeamlessVideoClip } from "../../components/video";
import type { VideoNode } from "./types";

export function buildClipFromVideoNode(node: VideoNode | null): SeamlessVideoClip | null {
  if (!node?.videoUri) {
    return null;
  }

  return {
    clipKey: node.nodeKey,
    src: node.videoUri,
    label: node.displayText,
  };
}

