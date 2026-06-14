import { createContext, useContext } from "react";

export type ResultTheme = "dark" | "light";

export const ResultThemeContext = createContext<ResultTheme>("dark");

export function useResultTheme(): ResultTheme {
  return useContext(ResultThemeContext);
}

/** 浅色主题下的文字/背景工具类映射 */
export const themeClasses = {
  /** 主标题 */
  title: { dark: "text-white", light: "text-slate-900" },
  /** 副标题/模块名 */
  subtitle: { dark: "text-sky-100/88", light: "text-slate-600" },
  /** 正文 */
  body: { dark: "text-white/72", light: "text-slate-500" },
  /** 数值 */
  value: { dark: "text-white", light: "text-slate-900" },
  /** 分数标签 */
  scoreLabel: { dark: "text-sky-100/80", light: "text-slate-500" },
  /** 分数值 */
  scoreValue: { dark: "text-sky-100/82", light: "text-slate-700" },
  /** 次要文字 */
  muted: { dark: "text-white/78", light: "text-slate-500" },
  /** 操作按钮 */
  actionBtn: {
    dark: "border-white/30 bg-white/[0.06] text-white hover:bg-white/[0.12]",
    light: "border-violet-200 bg-violet-50 text-violet-600 hover:bg-violet-100",
  },
  /** 量表行 */
  scaleRow: {
    dark: "border-white/10 bg-white/[0.03] hover:bg-white/[0.08]",
    light: "border-slate-200/60 bg-white/60 hover:bg-white",
  },
  /** 量表选中行 */
  scaleRowActive: {
    dark: "border-primary-300/70 bg-primary-500/10",
    light: "border-violet-300 bg-violet-50",
  },
  /** 查看详情链接 */
  detailLink: { dark: "text-primary-200", light: "text-violet-500" },
} as const;
