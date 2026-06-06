import type { ResultCardTone } from "./types";

export function getSeverityBadgeClasses(level?: string | null) {
  if (!level) {
    return "border-slate-200 bg-slate-100/70 text-slate-600";
  }

  if (level.includes("重度") || level.includes("危险")) {
    return "border-rose-200 bg-rose-50/80 text-rose-600";
  }

  if (level.includes("中度") || level.includes("关注")) {
    return "border-amber-200 bg-amber-50/80 text-amber-600";
  }

  if (level.includes("轻度") || level.includes("正常")) {
    return "border-emerald-200 bg-emerald-50/80 text-emerald-600";
  }

  return "border-primary-200 bg-primary-50/80 text-primary-600";
}

export function getToneClasses(tone: ResultCardTone = "blue") {
  switch (tone) {
    case "emerald":
      return {
        iconBg: "bg-emerald-100",
        iconText: "text-emerald-500",
        softBg: "bg-emerald-50/70",
        softBorder: "border-emerald-100/80",
        softText: "text-emerald-600",
      };
    case "indigo":
      return {
        iconBg: "bg-indigo-100",
        iconText: "text-indigo-500",
        softBg: "bg-indigo-50/70",
        softBorder: "border-indigo-100/80",
        softText: "text-indigo-600",
      };
    case "rose":
      return {
        iconBg: "bg-rose-100",
        iconText: "text-rose-500",
        softBg: "bg-rose-50/70",
        softBorder: "border-rose-100/80",
        softText: "text-rose-600",
      };
    case "amber":
      return {
        iconBg: "bg-amber-100",
        iconText: "text-amber-500",
        softBg: "bg-amber-50/70",
        softBorder: "border-amber-100/80",
        softText: "text-amber-600",
      };
    case "blue":
    default:
      return {
        iconBg: "bg-primary-100",
        iconText: "text-primary-600",
        softBg: "bg-primary-50/70",
        softBorder: "border-primary-100/80",
        softText: "text-primary-600",
      };
  }
}

export function getScaleTone(index: number): ResultCardTone {
  const tones: ResultCardTone[] = ["blue", "emerald", "indigo", "rose"];
  return tones[index % tones.length];
}
