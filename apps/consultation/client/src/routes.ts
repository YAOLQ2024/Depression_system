import type { AssessmentSession, ConsultationSession, UserRecord } from "./types";

export const APP_PATHS = {
  cover: "/",
  login: "/login",
  home: "/home",
  profile: "/profile",
  preparation: "/preparation",
  consultation: "/consultation",
  assessmentSelection: "/scale-selection",
  assessment: "/scale-questionnaire",
  result: "/result",
  intervention: "/intervention",
  interventionVideo: "/intervention/video",
  interventionGame: "/intervention/game",
  interventionStory: "/intervention/story",
  seamlessVideoDemo: "/labs/seamless-video-player",
  history: "/history",
  historyDetail: "/history/:id",
  historyScaleDetail: "/history/:id/scale/:scaleId",
} as const;

type ResolveAppPathArgs = {
  user: UserRecord | null;
  consultation: ConsultationSession | null;
  assessment: AssessmentSession | null;
};

function hasResumableConsultationSession(consultation: ConsultationSession | null) {
  if (!consultation) {
    return false;
  }

  return consultation.status !== "paused_for_human_review";
}

export function resolveResumePath({ user, consultation, assessment }: ResolveAppPathArgs) {
  if (!user) {
    return APP_PATHS.login;
  }

  if (assessment?.status === "completed") {
    return APP_PATHS.result;
  }

  if (assessment) {
    return APP_PATHS.assessment;
  }

  if (consultation?.status === "handoff_ready") {
    return APP_PATHS.assessmentSelection;
  }

  if (hasResumableConsultationSession(consultation)) {
    return APP_PATHS.consultation;
  }

  if (user.profile_status !== "completed") {
    return APP_PATHS.preparation;
  }

  return APP_PATHS.home;
}

export function resolvePostLoginPath(user: UserRecord | null) {
  return user ? APP_PATHS.home : APP_PATHS.login;
}

export function buildHistoryScaleDetailPath(encounterId: string, scaleId: string) {
  return `${APP_PATHS.history}/${encounterId}/scale/${scaleId}`;
}

export function resolveHomeEntryPath({ user, consultation, assessment }: ResolveAppPathArgs) {
  if (!user) {
    return APP_PATHS.login;
  }

  if (assessment?.status === "completed") {
    return APP_PATHS.result;
  }

  if (assessment) {
    return APP_PATHS.assessment;
  }

  if (consultation?.status === "handoff_ready") {
    return APP_PATHS.assessmentSelection;
  }

  if (hasResumableConsultationSession(consultation)) {
    return APP_PATHS.consultation;
  }

  return APP_PATHS.preparation;
}

export function resolveHomeEntryLabel({ user, consultation, assessment }: ResolveAppPathArgs) {
  if (!user) {
    return "立即登录";
  }

  if (assessment?.status === "completed") {
    return "查看结果";
  }

  if (assessment) {
    return "继续量表";
  }

  if (consultation?.status === "handoff_ready") {
    return "进入量表评估";
  }

  if (hasResumableConsultationSession(consultation)) {
    return "继续问诊";
  }

  return "开始问诊";
}

export function isPublicPath(pathname: string) {
  return pathname === APP_PATHS.cover || pathname === APP_PATHS.login;
}
