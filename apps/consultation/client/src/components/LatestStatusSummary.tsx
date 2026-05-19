import { ShieldAlert, ChevronRight, Music } from "lucide-react";
import { SoftCard } from "./SoftCard";
import { cn } from "../lib/utils";
import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip } from "recharts";

const mockEmotionData = [
  { day: "4/10", value: 3 },
  { day: "4/17", value: 2 },
  { day: "4/24", value: 4 },
  { day: "5/01", value: 2 },
  { day: "5/08", value: 4 },
  { day: "5/15", value: 3 },
  { day: "5/20", value: 3 }, // Map values: 1: normal, 2: mild, 3: moderate, 4: severe for visualization curve
];

export function LatestStatusSummary() {
  return (
    <div className="mb-4">
      <h3 className="text-lg font-semibold text-slate-800 mb-4 px-1">最近状态摘要</h3>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Risk Level */}
        <SoftCard className="p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2 text-orange-500 font-medium">
              <ShieldAlert className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">最近风险等级</span>
            </div>
            <div className="text-2xl font-bold text-orange-500 mb-1">中度风险</div>
            <div className="text-xs text-slate-500 mb-4">评估时间：2024-05-20</div>
          </div>
          <button className="flex items-center justify-between w-full py-1.5 px-3 rounded-lg border border-slate-200 text-sm text-primary-600 hover:bg-primary-50 transition-colors">
            查看详情 <ChevronRight className="w-4 h-4" />
          </button>
        </SoftCard>

        {/* Scale Summary */}
        <SoftCard className="p-5 flex flex-col">
          <h4 className="text-sm font-semibold text-slate-800 mb-3">量表结果摘要</h4>
          <div className="space-y-2 flex-1">
            {[
               { name: "PHQ-9", score: "15分", level: "中度", color: "text-orange-500", bg: "bg-orange-50" },
               { name: "SCL-90", score: "1.8分", level: "中度", color: "text-orange-500", bg: "bg-orange-50" },
               { name: "SDS", score: "56分", level: "中度", color: "text-orange-500", bg: "bg-orange-50" },
               { name: "SAS", score: "52分", level: "轻度", color: "text-green-500", bg: "bg-green-50" },
            ].map((item) => (
              <div key={item.name} className="flex items-center justify-between text-xs">
                <span className="text-slate-600 font-medium w-16">{item.name}</span>
                <span className="text-slate-500 w-12">{item.score}</span>
                <span className={cn("px-2 py-0.5 rounded text-[10px] font-medium inline-block min-w-10 text-center", item.color, item.bg)}>
                  {item.level}
                </span>
              </div>
            ))}
          </div>
        </SoftCard>

        {/* Emotion Trend */}
        <SoftCard className="p-5 flex flex-col">
          <h4 className="text-sm font-semibold text-slate-800 mb-1">情绪趋势（近7次）</h4>
          <div className="text-[10px] text-slate-400 mb-2 border-l border-slate-200 pl-1 ml-1 flex flex-col justify-between h-[80px] absolute left-4 mt-8 pointer-events-none">
            <span>重度</span><span>中度</span><span>轻度</span><span>正常</span>
          </div>
          <div className="flex-1 w-full h-[100px] min-w-0 pl-6 mt-1 overflow-hidden relative">
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <LineChart data={mockEmotionData} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4, fill: "#3b82f6", strokeWidth: 2, stroke: "#fff" }} />
                <YAxis domain={[1, 4]} hide />
              </LineChart>
            </ResponsiveContainer>
             <div className="flex justify-between w-full text-[9px] text-slate-400 mt-1 absolute bottom-0 px-1">
                {mockEmotionData.map(d => <span key={d.day}>{d.day}</span>)}
            </div>
          </div>
        </SoftCard>

        {/* Recent Intervention */}
        <SoftCard className="p-5 flex flex-col justify-between relative overflow-hidden">
          {/* subtle background decor */}
          <div className="absolute -right-6 -bottom-6 opacity-10">
            <Music className="w-24 h-24 text-primary-500" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-3">最近干预记录</h4>
            <div className="flex items-start gap-3 bg-white/60 p-3 rounded-xl border border-white mb-2">
              <div className="w-10 h-10 bg-indigo-100 text-indigo-500 rounded-lg flex items-center justify-center shrink-0">
                <Music className="w-5 h-5" />
              </div>
              <div>
                <div className="font-semibold text-slate-800 text-sm">舒缓音乐</div>
                <div className="text-xs text-slate-500">15 分钟</div>
              </div>
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-1">
               <span className="inline-block w-4 h-4 bg-slate-100 rounded flex items-center justify-center text-[10px]">🗓️</span> 2024-05-20 完成
            </div>
          </div>
          <button className="text-xs font-medium text-primary-600 text-right w-full mt-2 hover:underline">
            查看更多 &gt;
          </button>
        </SoftCard>
      </div>
    </div>
  );
}
