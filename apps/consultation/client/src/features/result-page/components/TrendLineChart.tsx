import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ResultTrendPoint } from "../types";
import { useResultTheme } from "../theme-context";
import { GlassCard } from "./GlassCard";

interface TrendLineChartProps {
  data: ResultTrendPoint[];
  className?: string;
  emptyLabel?: string;
}

export function TrendLineChart({
  data,
  className,
  emptyLabel = "历次得分趋势待接入",
}: TrendLineChartProps) {
  const theme = useResultTheme();
  const isDark = theme === "dark";

  return (
    <GlassCard className={`p-3 ${className || ""}`.trim()}>
      <h3 className={`mb-3 text-[15px] font-semibold ${isDark ? "text-white" : "text-slate-900"}`}>历次得分趋势</h3>
      <div className="h-[200px] w-full">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke={isDark ? "rgba(255,255,255,0.14)" : "rgba(148,163,184,0.26)"}
              />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fill: isDark ? "#E2E8F0" : "#64748B", fontSize: 13 }}
                dy={10}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: isDark ? "#E2E8F0" : "#64748B", fontSize: 13 }}
                domain={[0, "dataMax + 10"]}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: isDark ? "rgba(15,23,42,0.82)" : "rgba(255,255,255,0.96)",
                  backdropFilter: "blur(10px)",
                  borderRadius: "10px",
                  border: isDark ? "1px solid rgba(255,255,255,0.12)" : "1px solid rgba(148,163,184,0.18)",
                  boxShadow: isDark ? "0 12px 30px rgba(0,0,0,0.2)" : "0 12px 30px rgba(15,23,42,0.08)",
                  color: isDark ? "#F8FAFC" : "#0F172A",
                }}
                itemStyle={{ color: isDark ? "#93C5FD" : "#2563EB", fontWeight: 600 }}
                labelStyle={{ color: isDark ? "#E2E8F0" : "#475569", marginBottom: "4px" }}
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#3B82F6"
                strokeWidth={3}
                dot={{ r: 4, fill: "#fff", stroke: "#3B82F6", strokeWidth: 2 }}
                activeDot={{ r: 6, fill: "#3B82F6", stroke: "#fff", strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div
            className={`flex h-full items-center justify-center rounded-[8px] border border-dashed px-6 text-center text-sm ${
              isDark
                ? "border-white/16 bg-white/[0.03] text-sky-100/74"
                : "border-slate-200 bg-slate-50/70 text-slate-500"
            }`}
          >
            {emptyLabel}
          </div>
        )}
      </div>
    </GlassCard>
  );
}
