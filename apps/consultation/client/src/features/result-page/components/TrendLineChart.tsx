import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ResultTrendPoint } from "../types";
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
  return (
    <GlassCard className={`p-3 ${className || ""}`.trim()}>
      <h3 className="mb-3 text-[15px] font-semibold text-white">历次得分趋势</h3>
      <div className="h-[200px] w-full">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.14)" />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#E2E8F0", fontSize: 13 }}
                dy={10}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#E2E8F0", fontSize: 13 }}
                domain={[0, "dataMax + 10"]}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(15,23,42,0.82)",
                  backdropFilter: "blur(10px)",
                  borderRadius: "10px",
                  border: "1px solid rgba(255,255,255,0.12)",
                  boxShadow: "0 12px 30px rgba(0,0,0,0.2)",
                  color: "#F8FAFC",
                }}
                itemStyle={{ color: "#93C5FD", fontWeight: 600 }}
                labelStyle={{ color: "#E2E8F0", marginBottom: "4px" }}
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
          <div className="flex h-full items-center justify-center rounded-[8px] border border-dashed border-white/16 bg-white/[0.03] px-6 text-center text-sm text-sky-100/74">
            {emptyLabel}
          </div>
        )}
      </div>
    </GlassCard>
  );
}
