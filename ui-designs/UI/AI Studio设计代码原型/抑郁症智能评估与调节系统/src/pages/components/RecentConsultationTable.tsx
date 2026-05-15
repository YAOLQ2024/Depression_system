import { ChevronRight } from "lucide-react";
import { SoftCard } from "../../components/SoftCard";
import { cn } from "../../lib/utils";

const RECORDS = [
  { id: 1, time: "2024-05-20 14:30", type: "常规评估问诊", risk: "中度风险", score: "15分", status: "已完成" },
  { id: 2, time: "2024-05-06 16:15", type: "完整评估问诊", risk: "轻度风险", score: "8分", status: "已完成" },
  { id: 3, time: "2024-04-22 09:40", type: "随访问诊", risk: "轻度风险", score: "7分", status: "已完成" },
];

export function RecentConsultationTable() {
  return (
    <div className="mb-4">
      <h3 className="text-lg font-semibold text-slate-800 mb-4 px-1">最近问诊记录</h3>
      <SoftCard className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/60 text-xs font-semibold text-slate-500">
                <th className="py-3 px-6 font-medium">问诊时间</th>
                <th className="py-3 px-6 font-medium">问诊类型</th>
                <th className="py-3 px-6 font-medium">风险等级</th>
                <th className="py-3 px-6 font-medium">PHQ-9得分</th>
                <th className="py-3 px-6 font-medium">状态</th>
                <th className="py-3 px-6 font-medium">操作</th>
              </tr>
            </thead>
            <tbody className="text-sm text-slate-600">
              {RECORDS.map((record) => (
                <tr key={record.id} className="border-b border-slate-100 last:border-none hover:bg-slate-50/50 transition-colors">
                  <td className="py-3 px-6">{record.time}</td>
                  <td className="py-3 px-6">{record.type}</td>
                  <td className="py-3 px-6">
                    <span className={cn(
                      "font-medium tracking-tight",
                      record.risk === "中度风险" ? "text-orange-500" : "text-green-500"
                    )}>
                      {record.risk}
                    </span>
                  </td>
                  <td className="py-3 px-6">{record.score}</td>
                  <td className="py-3 px-6">
                    <span className="text-green-600">{record.status}</span>
                  </td>
                  <td className="py-3 px-6">
                    <button className="text-primary-600 hover:text-primary-700 font-medium flex items-center text-xs group">
                      查看报告 <ChevronRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-3 bg-slate-50/50 border-t border-slate-100 flex justify-center">
          <button className="text-sm text-primary-600 font-medium hover:underline flex items-center gap-1">
            查看更多记录 <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </SoftCard>
    </div>
  );
}
