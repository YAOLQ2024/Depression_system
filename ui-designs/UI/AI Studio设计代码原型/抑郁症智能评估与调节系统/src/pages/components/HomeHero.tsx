import { MessageSquare, FileText } from "lucide-react";

interface HomeHeroProps {
  onStart: () => void;
  userName: string;
}

export function HomeHero({ onStart, userName }: HomeHeroProps) {
  return (
    <div className="relative w-full overflow-hidden rounded-[2rem] bg-gradient-to-r from-blue-100/40 via-indigo-50/30 to-purple-100/20 p-6 shadow-soft border border-white/60 mb-3 flex items-center min-h-[200px] backdrop-blur-md">
      {/* Decorative Background Elements */}
      <div className="absolute top-0 right-0 w-full h-full overflow-hidden pointer-events-none">
         <div className="absolute top-10 right-20 w-64 h-64 rounded-full border border-white/40 blur-[1px]"></div>
         <div className="absolute -top-20 -right-10 w-96 h-96 rounded-full border-[1PX] border-indigo-200/50"></div>
         <div className="absolute top-1/2 right-1/4 w-32 h-32 bg-blue-300/20 rounded-full blur-3xl"></div>
      </div>
      
      {/* Abstract Brain/Medical Graphic on the Right */}
      <div className="absolute right-16 top-1/2 -translate-y-1/2 opacity-80 pointer-events-none hidden lg:block scale-125">
        <div className="relative">
          {/* Main glowing brain-like structure outline */}
          <svg width="220" height="180" viewBox="0 0 200 160" className="text-primary-500/30 fill-current drop-shadow-[0_0_20px_rgba(59,130,246,0.6)]">
            <path d="M100 20 C 130 -10, 190 20, 180 70 C 170 120, 130 140, 100 130 C 70 140, 30 120, 20 70 C 10 20, 70 -10, 100 20 Z" stroke="currentColor" strokeWidth="2" fill="none" />
            <circle cx="100" cy="80" r="4" className="text-blue-400 fill-current" />
            {/* Neural nodes */}
            <circle cx="60" cy="50" r="2" className="text-blue-400 fill-current" />
            <circle cx="140" cy="50" r="2" className="text-blue-400 fill-current" />
            <circle cx="150" cy="100" r="2" className="text-blue-400 fill-current" />
            <circle cx="50" cy="100" r="2" className="text-blue-400 fill-current" />
            {/* Connecting lines */}
            <path d="M100 80 L60 50 M100 80 L140 50 M100 80 L50 100 M100 80 L150 100" stroke="currentColor" strokeWidth="0.5" className="text-blue-300/40" />
          </svg>
          <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 w-40 h-8 bg-blue-500/20 blur-xl rounded-[100%]"></div>
          {/* Medical Shield icon overlay */}
          <div className="absolute bottom-4 right-0 bg-white/60 p-3 rounded-2xl shadow-glass backdrop-blur-xl border border-white/80">
             <FileText className="w-8 h-8 text-primary-500" />
          </div>
        </div>
      </div>

      <div className="flex z-10 w-full h-full items-center gap-8 relative max-w-2xl">
        {/* Welcome Content */}
        <div className="flex-1 space-y-3">
          <h2 className="text-3xl font-bold tracking-tight text-slate-800">
            您好，{userName}！我是您的数字人心理助手
          </h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            我将协助您完成心理状态评估、陪伴您关注心理健康，提供科学的意见与支持。
          </p>
          
          <div className="flex items-center gap-2 mt-4 mb-1">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/50 border border-slate-200/50 text-xs font-medium text-slate-500 shadow-sm backdrop-blur-md">
               <FileText className="w-4 h-4 text-primary-500" />
               当前状态：<span className="text-primary-600 cursor-pointer hover:underline">待开始问诊 &gt;</span>
            </span>
          </div>

          <button 
            onClick={onStart}
            className="flex items-center gap-2 bg-gradient-to-r from-primary-500 to-indigo-500 hover:from-primary-600 hover:to-indigo-600 text-white px-8 py-3 rounded-full font-medium shadow-[0_4px_15px_rgba(59,130,246,0.3)] transition-all duration-300 hover:-translate-y-0.5 text-base"
          >
            <MessageSquare className="w-5 h-5" fill="currentColor" fillOpacity={0.2} />
            开始问诊
          </button>
        </div>
      </div>
    </div>
  );
}
