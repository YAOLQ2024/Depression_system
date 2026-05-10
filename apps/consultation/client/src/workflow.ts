export const SIDEBAR_STEPS = [
  { title: "问诊准备", description: "填写基本信息" },
  { title: "数字人问诊", description: "AI 数字人沟通" },
  { title: "量表问诊", description: "心理量表评估" },
  { title: "结果分析", description: "评估结果与建议" },
] as const;

export const CONSULTATION_VISUAL_STEPS = [
  "主诉采集",
  "现病史",
  "睡眠饮食",
  "情绪体验",
  "高风险筛查",
  "总结建议",
] as const;

export const CONSULTATION_STAGE_MAP: Record<string, number> = {
  "stage-01-greeting-and-briefing": 1,
  "stage-02-chief-complaint": 1,
  "stage-03-current-history-followup": 2,
  "stage-04-high-risk-screening": 5,
  "handoff-to-scale-assessment": 6,
};

export function getConsultationVisualStep(stageId?: string | null) {
  if (!stageId) {
    return 1;
  }
  return CONSULTATION_STAGE_MAP[stageId] || 1;
}

export function getConsultationStageName(stageId?: string | null) {
  const stageNameMap: Record<string, string> = {
    "stage-01-greeting-and-briefing": "初始问候与流程说明",
    "stage-02-chief-complaint": "主诉采集",
    "stage-03-current-history-followup": "现病史规则式问诊",
    "stage-04-high-risk-screening": "高风险问题排查",
    "handoff-to-scale-assessment": "量表移交",
  };

  if (!stageId) {
    return "数字人问诊";
  }

  return stageNameMap[stageId] || stageId;
}
