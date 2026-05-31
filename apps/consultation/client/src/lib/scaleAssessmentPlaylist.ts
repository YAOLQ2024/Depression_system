import type { AssessmentCatalogItem } from "../types";

export type ScaleAssessmentPreviewQuestion = {
  questionKey: string;
  stageId: string;
  stageLabel: string;
  stageOrder: number;
  order: number;
  questionText: string;
  videoAssetId: string;
  videoUri: string;
  responseRequired: boolean;
};

export type ScaleAssessmentPreviewStage = {
  slug: string;
  code: string;
  stageLabel: string;
  stageOrder: number;
  timeframe: string;
  introText: string | null;
  introVideoUri: string | null;
  answerOptions: AssessmentCatalogItem["answer_options"];
  questions: ScaleAssessmentPreviewQuestion[];
};

function padQuestionNumber(order: number) {
  return String(order).padStart(3, "0");
}

function buildQuestionKey(slug: string, order: number) {
  return `${slug}-${padQuestionNumber(order)}`;
}

export function buildScaleAssessmentPreviewStages(catalog: AssessmentCatalogItem[]) {
  return catalog.map((item, index) => ({
    slug: item.slug,
    code: item.code,
    stageLabel: item.short_name || item.code,
    stageOrder: index + 1,
    timeframe: item.timeframe?.trim() || "当前阶段",
    introText: item.stage_intro_text?.trim() || null,
    introVideoUri: item.stage_intro_video_uri?.trim() || null,
    answerOptions: item.answer_options || [],
    questions: [...(item.items || [])]
      .sort((left, right) => left.index - right.index)
      .map((question) => {
        const questionKey = buildQuestionKey(item.slug, question.index);
        return {
          questionKey,
          stageId: item.slug,
          stageLabel: item.short_name || item.code,
          stageOrder: index + 1,
          order: question.index,
          questionText: question.question_text?.trim() || question.text,
          videoAssetId: questionKey,
          videoUri: question.video_uri?.trim() || `/digital-human/scale-assessment-v1/${questionKey}.webm`,
          responseRequired: true,
        };
      }),
  }));
}
