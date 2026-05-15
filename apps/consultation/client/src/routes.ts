import type { AssessmentSession, ConsultationSession, UserRecord } from "./types";

export const APP_PATHS = {
  cover: "/",
  login: "/login",
  home: "/home",
  preparation: "/preparation",
  consultation: "/consultation",
  assessment: "/scale-questionnaire",
  result: "/result",
  intervention: "/intervention",
} as const;

type ResolveAppPathArgs = {
  user: UserRecord | null;
  consultation: ConsultationSession | null;
  assessment: AssessmentSession | null;
};

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

  if (consultation) {
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

  if (consultation) {
    return APP_PATHS.consultation;
  }

  if (user.profile_status !== "completed") {
    return APP_PATHS.preparation;
  }

  return APP_PATHS.consultation;
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

  if (consultation) {
    return "继续问诊";
  }

  return "开始问诊";
}

export function isPublicPath(pathname: string) {
  return pathname === APP_PATHS.cover || pathname === APP_PATHS.login;
}
