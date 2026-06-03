import type { AssessmentItem } from "../../types";
import type { ScaleAssessmentPreviewQuestion, ScaleAssessmentPreviewStage } from "../../lib/scaleAssessmentPlaylist";
import { normalizeVideoNodeUri, type VideoNode } from "./types";

export type BuildAssessmentCurrentVideoNodeParams = {
  currentStage: ScaleAssessmentPreviewStage | null;
  currentQuestion: ScaleAssessmentPreviewQuestion | null;
  currentQuestionKey: string | null;
  currentItem: AssessmentItem | null;
  hasPendingStageIntro: boolean;
};

function resolveAssessmentQuestionText(
  currentQuestion: ScaleAssessmentPreviewQuestion | null,
  currentItem: AssessmentItem | null,
) {
  return currentQuestion?.questionText?.trim() || currentItem?.text?.trim() || "";
}

// Step 1 maps both stage intros and assessment questions into VideoNode so the
// next steps can plug them into one shared player/controller pipeline.
export function buildAssessmentCurrentVideoNode({
  currentStage,
  currentQuestion,
  currentQuestionKey,
  currentItem,
  hasPendingStageIntro,
}: BuildAssessmentCurrentVideoNodeParams): VideoNode | null {
  const normalizedQuestionKey = currentQuestionKey?.trim() || null;
  if (!currentStage || !normalizedQuestionKey) {
    return null;
  }

  if (hasPendingStageIntro && currentStage.introText?.trim()) {
    const introNodeKey = `${currentStage.slug}-000`;
    const displayText = currentStage.introText.trim();
    return {
      nodeKey: introNodeKey,
      questionKey: normalizedQuestionKey,
      sessionKind: "assessment",
      source: "assessment_stage_intro",
      transitionMode: "local_only",
      stageId: currentStage.slug,
      stageLabel: currentStage.stageLabel,
      stageOrder: currentStage.stageOrder,
      videoAssetId: introNodeKey,
      videoUri: normalizeVideoNodeUri(currentStage.introVideoUri),
      displayText,
      subtitleText: displayText,
      responseRequired: false,
    };
  }

  const displayText = resolveAssessmentQuestionText(currentQuestion, currentItem);
  return {
    nodeKey: normalizedQuestionKey,
    questionKey: normalizedQuestionKey,
    sessionKind: "assessment",
    source: "assessment_question",
    transitionMode: "submit_driven",
    stageId: currentStage.slug,
    stageLabel: currentStage.stageLabel,
    stageOrder: currentStage.stageOrder,
    videoAssetId: currentQuestion?.videoAssetId || normalizedQuestionKey,
    videoUri: normalizeVideoNodeUri(currentQuestion?.videoUri),
    displayText,
    subtitleText: displayText,
    responseRequired: true,
  };
}

export function isAssessmentStageIntroVideoNode(node: VideoNode | null) {
  return node?.source === "assessment_stage_intro";
}

