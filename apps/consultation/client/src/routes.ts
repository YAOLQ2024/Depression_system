import type { AssessmentSession, ConsultationSession, UserRecord } from "./types";

export const APP_PATHS = {
  cover: "/",
  login: "/login",
  preparation: "/prepare",
  consultationEntry: "/consultation/start",
  consultation: "/consultation",
  assessment: "/assessment",
  result: "/result",
} as const;

type ResolveAppPathArgs = {
  user: UserRecord | null;
  consultation: ConsultationSession | null;
  assessment: AssessmentSession | null;
};

export function resolveAppPath({ user, consultation, assessment }: ResolveAppPathArgs) {
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

  return APP_PATHS.consultationEntry;
}

export function isPublicPath(pathname: string) {
  return pathname === APP_PATHS.cover || pathname === APP_PATHS.login;
}
