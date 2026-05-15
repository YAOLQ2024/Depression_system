import { MessageSquareDashed, Leaf, CheckSquare, UserCircle, ChevronRight } from "lucide-react";
import { SoftCard } from "./SoftCard";

const ACTIONS = [
  { 
    title: "历史记录", 
    desc: "查看问诊与评估记录", 
    icon: MessageSquareDashed, 
    color: "bg-blue-100 text-blue-600",
    iconBg: "bg-blue-500 text-white"
  },
  { 
    title: "调节干预", 
    desc: "放松训练与心理调节", 
    icon: Leaf, 
    color: "bg-green-100 text-green-600",
    iconBg: "bg-green-500 text-white"
  },
  { 
    title: "再评估", 
    desc: "定期评估心理状态", 
    icon: CheckSquare, 
    color: "bg-purple-100 text-purple-600",
    iconBg: "bg-purple-500 text-white"
  },
  { 
    title: "个人档案", 
    desc: "管理个人基本信息", 
    icon: UserCircle, 
    color: "bg-orange-100 text-orange-600",
    iconBg: "bg-orange-500 text-white"
  },
];

export function QuickActions() {
  return (
    <div className="mb-4">
      <h3 className="text-lg font-semibold text-slate-800 mb-4 px-1">快捷功能</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {ACTIONS.map((action, i) => (
          <SoftCard key={i} className="p-4 flex items-center justify-between group">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${action.iconBg} shadow-sm group-hover:scale-105 transition-transform`}>
                <action.icon className="w-5 h-5 drop-shadow-sm" />
              </div>
              <div>
                <h4 className="font-semibold text-slate-800 text-sm group-hover:text-primary-600 transition-colors">{action.title}</h4>
                <p className="text-xs text-slate-500 mt-0.5">{action.desc}</p>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-primary-400 group-hover:translate-x-0.5 transition-all" />
          </SoftCard>
        ))}
      </div>
    </div>
  );
}
