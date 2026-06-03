import type { ConsultationSession } from "../../types";
import { normalizeVideoNodeUri, type VideoNode } from "./types";

function resolveConsultationVideoNodeDisplayText(session: ConsultationSession | null) {
  const questionText = session?.current_question_text?.trim() || session?.current_question_item?.question_text?.trim();
  if (questionText) {
    return questionText;
  }

  const stageLabel = session?.current_stage?.stage_label || session?.current_question_item?.stage_label;
  if (stageLabel) {
    return `当前处于“${stageLabel}”阶段，题目文案待加载。`;
  }

  return "当前题目内容待加载。";
}

function resolveConsultationVideoNodeSubtitleText(
  session: ConsultationSession | null,
  displayText: string,
) {
  return (
    session?.current_question_subtitle_text?.trim() ||
    session?.current_question_item?.subtitle_text?.trim() ||
    displayText
  );
}

export function buildConsultationCurrentVideoNode(session: ConsultationSession | null): VideoNode | null {
  const questionKey =
    session?.current_question_key?.trim() || session?.current_question_item?.question_key?.trim() || null;
  if (!questionKey) {
    return null;
  }

  // Consultation system prompts and answerable prompts both surface as
  // VideoNodes so later preview/commit work can share one transition model.
  const responseRequired = session?.current_question_item?.response_required ?? session?.status === "waiting_user_input";
  const displayText = resolveConsultationVideoNodeDisplayText(session);

  return {
    nodeKey: session?.current_node_id?.trim() || session?.current_question_item?.node_id?.trim() || questionKey,
    questionKey,
    sessionKind: "consultation",
    source: responseRequired ? "consultation_question" : "consultation_system_question",
    transitionMode: responseRequired ? "submit_driven" : "auto_commit",
    stageId: session?.current_stage_id || session?.current_question_item?.stage_id || null,
    stageLabel: session?.current_stage?.stage_label || session?.current_question_item?.stage_label || null,
    stageOrder: session?.current_stage?.stage_order ?? session?.current_question_item?.stage_order ?? null,
    videoAssetId:
      session?.current_question_video_asset_id?.trim() ||
      session?.current_question_item?.video_asset_id?.trim() ||
      questionKey,
    videoUri: normalizeVideoNodeUri(
      session?.current_question_video_uri || session?.current_question_item?.video_uri || null,
    ),
    displayText,
    subtitleText: resolveConsultationVideoNodeSubtitleText(session, displayText),
    responseRequired,
  };
}
