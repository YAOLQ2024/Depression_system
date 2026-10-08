import type { ConsultationSession } from "../../types";
import { normalizeVideoNodeUri, type VideoNode } from "./types";

const TRANSPARENT_RISK_VIDEO_ASSET_ID = "risk-screening-review-002";
const TRANSPARENT_RISK_VIDEO_URI =
  "/digital-human/consultation-v1/risk-screening-review-002.webm";
const TRANSPARENT_RISK_VIDEO_VERSION = "20260908-alpha";
// Stop four frames before the visual-empty tail (30 fps).
const TRANSPARENT_RISK_VIDEO_END_TIME_SECONDS = 6.000;

function resolveConsultationVideoUri(
  videoAssetId: string,
  candidate?: string | null,
) {
  const videoUri = normalizeVideoNodeUri(candidate);
  if (videoUri && videoAssetId === TRANSPARENT_RISK_VIDEO_ASSET_ID) {
    const sourcePath = videoUri.split(/[?#]/, 1)[0];
    if (sourcePath === TRANSPARENT_RISK_VIDEO_URI) {
      return `${TRANSPARENT_RISK_VIDEO_URI}?v=${TRANSPARENT_RISK_VIDEO_VERSION}#t=0,${TRANSPARENT_RISK_VIDEO_END_TIME_SECONDS}`;
    }
  }
  return videoUri;
}

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
  const videoAssetId =
    session?.current_question_video_asset_id?.trim() ||
    session?.current_question_item?.video_asset_id?.trim() ||
    questionKey;

  return {
    nodeKey: session?.current_node_id?.trim() || session?.current_question_item?.node_id?.trim() || questionKey,
    questionKey,
    sessionKind: "consultation",
    source: responseRequired ? "consultation_question" : "consultation_system_question",
    transitionMode: responseRequired ? "submit_driven" : "auto_commit",
    stageId: session?.current_stage_id || session?.current_question_item?.stage_id || null,
    stageLabel: session?.current_stage?.stage_label || session?.current_question_item?.stage_label || null,
    stageOrder: session?.current_stage?.stage_order ?? session?.current_question_item?.stage_order ?? null,
    videoAssetId,
    videoUri: resolveConsultationVideoUri(
      videoAssetId,
      session?.current_question_video_uri || session?.current_question_item?.video_uri || null,
    ),
    displayText,
    subtitleText: resolveConsultationVideoNodeSubtitleText(session, displayText),
    responseRequired,
  };
}
