import type { UserRecord } from "../types";

export function getUserDisplayName(user: UserRecord | null | undefined) {
  if (!user) {
    return "未登录";
  }

  const normalized = user.full_name?.trim();
  if (normalized) {
    return normalized;
  }

  return user.email?.split("@")[0] || "未命名用户";
}

export function getUserInitial(user: UserRecord | null | undefined) {
  return getUserDisplayName(user).slice(0, 1).toUpperCase();
}

export function getRoleLabel(role?: string | null) {
  switch (role) {
    case "participant":
      return "受试者";
    case "researcher":
      return "研究员";
    case "admin":
      return "管理员";
    default:
      return role || "未知角色";
  }
}

export function getProfileStatusLabel(status?: string | null) {
  switch (status) {
    case "completed":
      return "档案已完成";
    case "draft":
      return "档案待完善";
    default:
      return "状态未知";
  }
}
