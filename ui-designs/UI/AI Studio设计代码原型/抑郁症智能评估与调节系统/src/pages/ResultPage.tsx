import { useNavigate } from "react-router-dom";
import { ConsultationLayout } from "../layouts";
import { FileText, ChevronRight, Activity, Smile, Brain, Shield, RefreshCw, Pill } from "lucide-react";
import { cn } from "../lib/utils";

export default function ResultPage() {
  const navigate = useNavigate();

  return (
    <ConsultationLayout backgroundImage="/bg.png" title="评估结果">
      <div className="w-full h-full flex flex-col items-center overflow-y-auto pt-6 pb-12 px-4 md:px-8">
        
        {/* Title */}
        <div className="flex items-center gap-4 mb-8">
          <div className="h-[1px] w-12 bg-gradient-to-r from-transparent to-indigo-400"></div>
          <div className="w-2 h-2 rounded-full bg-indigo-400"></div>
          <h2 className="text-3xl font-bold text-[#1e293b] tracking-wider text-center drop-shadow-sm text-transparent bg-clip-text bg-gradient-to-r from-indigo-900 to-purple-800">
            评估结果
          </h2>
          <div className="w-2 h-2 rounded-full bg-indigo-400"></div>
          <div className="h-[1px] w-12 bg-gradient-to-l from-transparent to-indigo-400"></div>
        </div>

        <div className="w-full max-w-[1000px] flex flex-col gap-4">
          
          {/* Main Score Card */}
          <div className="w-full bg-white/40 backdrop-blur-xl border border-white/60 rounded-[32px] p-8 md:p-10 shadow-[0_8px_32px_rgba(31,38,135,0.1)] relative overflow-hidden flex flex-col md:flex-row shadow-indigo-500/10">
            {/* Splitter */}
            <div className="hidden md:block absolute left-1/2 top-10 bottom-10 w-[1px] bg-gradient-to-b from-transparent via-indigo-300/50 to-transparent"></div>

            {/* Left side: Total Score */}
            <div className="flex-1 flex flex-col items-center justify-center relative z-10 w-full mb-8 md:mb-0">
              <h3 className="text-xl font-medium text-slate-700 mb-2">总分</h3>
              <div className="flex items-baseline justify-center mb-6">
                 <span className="text-8xl font-bold text-transparent bg-clip-text bg-gradient-to-b from-indigo-500 to-blue-600 drop-shadow-sm">68</span>
                 <span className="text-2xl font-medium text-slate-500 ml-2">/ 100</span>
              </div>
              <div className="flex items-start gap-2 text-sm text-slate-600 bg-white/30 rounded-full px-4 py-2 border border-white/40">
                <div className="w-4 h-4 rounded-full border border-indigo-400 flex items-center justify-center mt-0.5 shrink-0 text-indigo-500 font-serif italic text-xs">i</div>
                <p>总分由各量表加权得出，反映当前整体心理健康状况。</p>
              </div>
            </div>

            {/* Right side: Severity */}
            <div className="flex-1 flex flex-col items-center justify-center relative z-10 w-full">
               <Brain className="absolute opacity-[0.03] w-64 h-64 top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-indigo-900 pointer-events-none" />
               <h3 className="text-xl font-medium text-slate-700 mb-6 relative z-10">疾病严重程度</h3>
               <div className="relative z-10 bg-gradient-to-b from-amber-50 to-orange-50 border border-orange-200/60 rounded-2xl px-10 py-6 shadow-inner shadow-orange-100/50">
                  <span className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-amber-500 to-orange-500 tracking-wide drop-shadow-sm">中度抑郁</span>
               </div>
            </div>
          </div>

          {/* Sub Score Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full">
            {/* PHQ-9 */}
            <div className="bg-white/40 backdrop-blur-xl border border-white/60 rounded-2xl p-5 flex items-center gap-4 shadow-sm relative overflow-hidden group hover:bg-white/50 transition-colors">
              <div className="absolute opacity-20 -right-4 -bottom-4 w-20 h-20 bg-indigo-200 rounded-full blur-2xl group-hover:bg-indigo-300 transition-colors"></div>
              <div className="w-12 h-12 rounded-xl bg-indigo-100/80 flex items-center justify-center border border-indigo-200/50">
                <FileText className="w-6 h-6 text-indigo-500" />
              </div>
              <div className="flex flex-col flex-1 z-10">
                <span className="text-sm font-medium text-slate-600">PHQ-9</span>
                <div className="flex items-baseline">
                  <span className="text-2xl font-bold text-slate-800">16</span>
                  <span className="text-sm font-medium text-slate-500 ml-1">/ 27</span>
                </div>
                <div className="h-1 w-full bg-slate-200/50 rounded-full mt-2 overflow-hidden">
                  <div className="h-full bg-indigo-500 rounded-full" style={{ width: '59%' }}></div>
                </div>
              </div>
            </div>

            {/* SDS */}
            <div className="bg-white/40 backdrop-blur-xl border border-white/60 rounded-2xl p-5 flex items-center gap-4 shadow-sm relative overflow-hidden group hover:bg-white/50 transition-colors">
              <div className="absolute opacity-20 -right-4 -bottom-4 w-20 h-20 bg-blue-200 rounded-full blur-2xl group-hover:bg-blue-300 transition-colors"></div>
              <div className="w-12 h-12 rounded-xl bg-blue-100/80 flex items-center justify-center border border-blue-200/50">
                <Smile className="w-6 h-6 text-blue-500" />
              </div>
              <div className="flex flex-col flex-1 z-10">
                <span className="text-sm font-medium text-slate-600">SDS</span>
                <div className="flex items-baseline">
                  <span className="text-2xl font-bold text-slate-800">56</span>
                  <span className="text-sm font-medium text-slate-500 ml-1">/ 80</span>
                </div>
                <div className="h-1 w-full bg-slate-200/50 rounded-full mt-2 overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: '70%' }}></div>
                </div>
              </div>
            </div>

            {/* SAS */}
            <div className="bg-white/40 backdrop-blur-xl border border-white/60 rounded-2xl p-5 flex items-center gap-4 shadow-sm relative overflow-hidden group hover:bg-white/50 transition-colors">
              <div className="absolute opacity-20 -right-4 -bottom-4 w-20 h-20 bg-purple-200 rounded-full blur-2xl group-hover:bg-purple-300 transition-colors"></div>
              <div className="w-12 h-12 rounded-xl bg-purple-100/80 flex items-center justify-center border border-purple-200/50">
                <Activity className="w-6 h-6 text-purple-500" />
              </div>
              <div className="flex flex-col flex-1 z-10">
                <span className="text-sm font-medium text-slate-600">SAS</span>
                <div className="flex items-baseline">
                  <span className="text-2xl font-bold text-slate-800">45</span>
                  <span className="text-sm font-medium text-slate-500 ml-1">/ 80</span>
                </div>
                <div className="h-1 w-full bg-slate-200/50 rounded-full mt-2 overflow-hidden">
                  <div className="h-full bg-purple-500 rounded-full" style={{ width: '56%' }}></div>
                </div>
              </div>
            </div>

            {/* Social Function */}
            <div className="bg-white/40 backdrop-blur-xl border border-white/60 rounded-2xl p-5 flex items-center gap-4 shadow-sm relative overflow-hidden group hover:bg-white/50 transition-colors">
              <div className="absolute opacity-20 -right-4 -bottom-4 w-20 h-20 bg-indigo-300 rounded-full blur-2xl group-hover:bg-indigo-400 transition-colors"></div>
              <div className="w-12 h-12 rounded-xl bg-indigo-100/80 flex items-center justify-center border border-indigo-300/50">
                <svg className="w-6 h-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <div className="flex flex-col flex-1 z-10">
                <span className="text-sm font-medium text-slate-600">社会功能</span>
                <div className="flex items-baseline">
                  <span className="text-2xl font-bold text-slate-800">40</span>
                  <span className="text-sm font-medium text-slate-500 ml-1">/ 100</span>
                </div>
                <div className="h-1 w-full bg-slate-200/50 rounded-full mt-2 overflow-hidden">
                  <div className="h-full bg-indigo-600 rounded-full" style={{ width: '40%' }}></div>
                </div>
              </div>
            </div>
          </div>

          {/* Recommendations Card */}
          <div className="w-full bg-white/40 backdrop-blur-xl border border-white/60 rounded-[24px] p-6 shadow-sm relative overflow-hidden mt-2">
            <div className="absolute right-0 bottom-0 opacity-[0.02] transform translate-x-1/4 translate-y-1/4 pointer-events-none">
               <Shield className="w-64 h-64 text-indigo-900" />
            </div>

            <div className="flex items-center gap-3 mb-4 relative z-10">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center shadow-inner">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-slate-800">就诊建议</h3>
            </div>

            <ul className="flex flex-col gap-3 relative z-10 list-none pl-2">
              <li className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-2 shrink-0"></div>
                <span className="text-slate-700 leading-relaxed text-[15px]">建议尽快预约精神心理科或心理门诊进行专业评估。</span>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-2 shrink-0"></div>
                <span className="text-slate-700 leading-relaxed text-[15px]">在医生指导下考虑心理治疗或药物治疗方案。</span>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-2 shrink-0"></div>
                <span className="text-slate-700 leading-relaxed text-[15px]">若出现自伤想法或情绪明显恶化，请及时就医。</span>
              </li>
            </ul>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-row justify-center items-center gap-4 lg:gap-8 mt-6">
            <button className="flex items-center justify-center gap-2 px-8 py-3.5 rounded-full bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-medium shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50 hover:scale-105 active:scale-95 transition-all w-[240px]">
              <FileText className="w-5 h-5" />
              查看完整报告
            </button>
            <button 
              onClick={() => navigate('/intervention')}
              className="flex items-center justify-center gap-2 px-8 py-3.5 rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-medium shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:scale-105 active:scale-95 transition-all w-[240px]">
              <Pill className="w-5 h-5" />
              进入调节干预
            </button>
            <button 
              onClick={() => navigate('/')}
              className="flex items-center justify-center gap-2 px-8 py-3.5 rounded-full bg-white/30 backdrop-blur-md border border-white/60 text-slate-700 font-medium hover:bg-white/50 hover:scale-105 active:scale-95 transition-all w-[240px]"
            >
              <RefreshCw className="w-5 h-5" />
              重新评估
            </button>
          </div>

        </div>
      </div>
    </ConsultationLayout>
  );
}
