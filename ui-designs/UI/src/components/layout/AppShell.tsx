import React from 'react';
import { LayoutDashboard, Users, FileText, BarChart3, HelpCircle, Shield, Bell, ChevronDown } from 'lucide-react';
import { PageState, User } from '../../types';
import { motion } from 'motion/react';
import FloatingBubbles from './FloatingBubbles';

interface AppShellProps {
  children: React.ReactNode;
  currentPage: PageState;
  onPageChange: (page: PageState) => void;
  user: User;
}

const AppShell: React.FC<AppShellProps> = ({ children, currentPage, onPageChange, user }) => {
  const sidebarItems = [
    { id: 'preparation', label: '问诊准备', icon: Users, desc: '填写基本信息' },
    { id: 'consultation', label: '数字人问诊', icon: LayoutDashboard, desc: 'AI 数字人沟通' },
    { id: 'assessment', label: '量表问诊', icon: FileText, desc: '心理量表评估' },
    { id: 'result', label: '结果分析', icon: BarChart3, desc: '评估结果与建议' },
  ];

  if (currentPage === 'auth') {
    return (
      <div className="relative min-h-screen w-full bg-[#F5F8FF] overflow-hidden font-sans">
        <FloatingBubbles />
        <div className="relative z-10">
          {children}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full bg-[#F5F8FF] overflow-hidden font-sans relative">
      <FloatingBubbles />
      
      {/* Sidebar */}
      <aside className="w-64 bg-gradient-to-b from-[#0F6BFF] to-[#0A4BB3] flex flex-col shrink-0 relative z-10">
        <div className="p-6 flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-xl backdrop-blur-md flex items-center justify-center">
            <div className="w-6 h-6 bg-white rounded-full flex items-center justify-center">
              <div className="w-3 h-3 bg-[#0F6BFF] rounded-sm rotate-45" />
            </div>
          </div>
          <h1 className="text-white font-bold text-lg leading-tight">
            抑郁症辅助问诊系统
          </h1>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-4">
          {sidebarItems.map((item) => {
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onPageChange(item.id as PageState)}
                className={`w-full group relative flex items-center gap-4 p-4 rounded-2xl transition-all duration-300 ${
                  isActive
                    ? 'bg-white shadow-lg shadow-blue-900/20'
                    : 'text-white/70 hover:bg-white/10 hover:text-white'
                }`}
              >
                <div className={`p-2 rounded-xl transition-colors ${isActive ? 'bg-[#0F6BFF] text-white' : 'bg-white/10 text-white'}`}>
                  <item.icon size={20} />
                </div>
                <div className="text-left">
                  <div className={`font-semibold text-sm ${isActive ? 'text-[#172033]' : 'text-white'}`}>{item.label}</div>
                  <div className={`text-[10px] ${isActive ? 'text-[#6B7893]' : 'text-white/50'}`}>{item.desc}</div>
                </div>
                {isActive && (
                  <motion.div
                    layoutId="active-indicator"
                    className="absolute -right-2 w-2 h-2 bg-emerald-400 rounded-full border-2 border-white shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                  />
                )}
              </button>
            );
          })}
        </nav>

        <div className="p-6 space-y-4">
          <button className="w-full h-11 bg-white/10 hover:bg-white/20 text-white text-sm font-medium rounded-xl flex items-center gap-2 justify-center transition-colors">
            <HelpCircle size={18} />
            使用指南
          </button>
          
          <div className="relative overflow-hidden h-32 rounded-3xl bg-blue-400/20 flex flex-col items-center justify-center p-4">
            <div className="absolute top-0 right-0 w-16 h-16 bg-white/5 rounded-full -mr-8 -mt-8" />
            <div className="absolute bottom-0 left-0 w-12 h-12 bg-blue-500/10 rounded-full -ml-4 -mb-4" />
            <div className="text-white/60 text-[10px] text-center mb-1">守护您的心理健康</div>
            <div className="w-16 h-16 bg-white/10 rounded-2xl flex items-center justify-center mb-2">
               <Shield size={32} className="text-white/40" />
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative min-w-0">
        {/* Header */}
        <header className="h-16 bg-white/80 backdrop-blur-md border-b border-[#E6EEFB] px-6 flex items-center justify-between z-10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-[#6B7893] text-xs">当前环节 /</span>
            <span className="text-[#172033] font-semibold text-sm">
              {sidebarItems.find(i => i.id === currentPage)?.label || '主页'}
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="px-3 py-1.5 bg-blue-50 rounded-full flex items-center gap-2 border border-blue-100 hidden sm:flex">
               <Shield size={14} className="text-[#0F6BFF]" />
               <span className="text-[#0F6BFF] text-[10px] font-medium uppercase">医疗级数据安全保护中</span>
               <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
            </div>

            <button className="relative w-8 h-8 flex items-center justify-center text-[#6B7893] hover:text-[#0F6BFF] transition-colors">
              <Bell size={18} />
              <div className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-rose-500 rounded-full border-2 border-white" />
            </button>

            <div className="h-6 w-[1px] bg-[#E6EEFB]" />

            <div className="flex items-center gap-2 group cursor-pointer">
              <div className="text-right hidden sm:block">
                <div className="text-[#172033] font-semibold text-xs">{user.name}</div>
                <div className="text-[#6B7893] text-[9px]">ID: {user.id}</div>
              </div>
              <div className="w-8 h-8 rounded-full p-0.5 border border-[#E6EEFB] group-hover:border-[#0F6BFF] transition-colors overflow-hidden">
                <img src={user.avatar} alt={user.name} className="w-full h-full rounded-full object-cover" />
              </div>
              <ChevronDown size={14} className="text-[#6B7893]" />
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-auto p-4 sm:p-6 relative">
          <motion.div
            key={currentPage}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="h-full w-full max-w-full"
          >
            {children}
          </motion.div>
        </div>
      </main>
    </div>
  );
};

export default AppShell;
