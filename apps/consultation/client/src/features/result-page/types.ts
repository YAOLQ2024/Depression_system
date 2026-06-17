import type { ReactNode } from "react";

export type ResultCardTone = "blue" | "emerald" | "indigo" | "rose" | "amber";

export type ResultScaleBrief = {
  id: string;
  name: string;
  fullName?: string | null;
  score?: number | null;
  maxScore?: number | null;
  scoreLabel?: string | null;
  severity?: string | null;
};

export type ResultTrendPoint = {
  date: string;
  score: number;
};

export type ResultScaleItem = {
  no: number | string;
  label: string;
  answerLabel?: string | null;
  answerScore?: number | null;
  answerSource?: string | null;
  transcriptText?: string | null;
};

export type ResultRiskFlag = {
  flag: string;
  label: string;
  itemId?: string | null;
  scoreValue?: number | null;
};

export type ResultAdvice = {
  title: string;
  content: string;
  icon?: ReactNode;
  tone?: ResultCardTone;
};

export type ResultModuleCard = {
  id: string;
  name: string;
  value?: string | number | null;
  description?: string | null;
  icon?: ReactNode;
  tone?: ResultCardTone;
  actionLabel?: string | null;
  onAction?: (() => void) | null;
};

export type ResultConsultationSummarySection = {
  id: string;
  title: string;
  content: string;
};

export type ResultConsultationSummary = {
  id: string;
  title: string;
  description: string;
  overallSummary: string;
  sections: ResultConsultationSummarySection[];
  linkedScales: string[];
  linkedScaleLabels: string[];
};

export type ResultDetailPanelData = {
  id: string;
  title: string;
  name?: string | null;
  fullName?: string | null;
  completedAt?: string | null;
  score?: number | null;
  maxScore?: number | null;
  normalizedScore?: number | null;
  severity?: string | null;
  riskLabel?: string | null;
  interpretation?: string | null;
  riskHint?: string | null;
  // Reserved for the future scale detail / risk-service advice contract.
  clinicalAdvice?: string | null;
  lifestyleAdvice?: string | null;
  riskFlags?: ResultRiskFlag[];
  answeredItemCount?: number | null;
  configuredItemCount?: number | null;
  scoreMethodLabel?: string | null;
  verificationStatus?: string | null;
  itemResultsReady?: boolean;
  itemResultsNotice?: string | null;
  history?: ResultTrendPoint[];
  items?: ResultScaleItem[];
};

export type ResultPageViewModel = {
  hasAssessment: boolean;
  assessmentSessionId: string | null;
  encounterSessionId: string | null;
  status: string;
  defaultScaleId: string | null;
  // Reserved for the future top-level risk-service contract.
  overallScore: number | null;
  overallScorePending: boolean;
  overallSeverity: string | null;
  overallSeverityPending: boolean;
  overallRiskLevel: string | null;
  overallRiskLevelPending: boolean;
  overallRiskReason: string | null;
  modules: ResultModuleCard[];
  scales: ResultScaleBrief[];
  scaleDetails: Record<string, ResultDetailPanelData>;
  consultationSummary: ResultConsultationSummary | null;
  // Reserved for the future top-level risk-service advice contract.
  clinicalAdvice: string | null;
  lifestyleAdvice: string | null;
  flattenedRiskFlags: Array<Record<string, unknown>>;
};
