import React, { useState } from 'react';
import { 
  ChevronLeft, ChevronRight, Mic, Video, Maximize2, Shield, Heart,
  Activity, Info, Timer, Pause
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { assessmentSteps, phq9Questions, multimodalStatuses, mockUser } from '../mockData';

interface AssessmentPageProps {
  onComplete: () => void;
}

const AssessmentPage: React.FC<AssessmentPageProps> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [currentQuestion, setCurrentQuestion] = useState(1);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);

  const handleNext = () => {
    if (currentQuestion < phq9Questions.length) {
      setCurrentQuestion(currentQuestion + 1);
      setSelectedOption(null);
    } else if (currentStep < assessmentSteps.length - 1) {
      setCurrentStep(currentStep + 1);
      setCurrentQuestion(1);
      setSelectedOption(null);
    } else {
      onComplete();
    }
  };

  const currentQData = phq9Questions[currentQuestion - 1] || phq9Questions[0];

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Questionnaire Steps */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#E6EEFB] flex items-center justify-between">
        <div className="flex items-center gap-6 flex-1 px-4">
          {assessmentSteps.map((step, idx) => (
            <div key={step.id} className="relative flex flex-col items-center gap-1 group flex-1">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-[10px] z-10 transition-all duration-300 ${
                idx < currentStep ? 'bg-blue-600 text-white' : 
                idx === currentStep ? 'bg-blue-600 text-white ring-4 ring-blue-50' : 
                'bg-[#F5F8FF] text-[#6B7893]'
              }`}>
                {idx < currentStep ? '✓' : idx + 1}
              </div>
              <span className={`text-[10px] font-bold transition-colors ${idx === currentStep ? 'text-[#172033]' : 'text-[#6B7893]'}`}>
                {step.id}
              </span>
              
              {idx < assessmentSteps.length - 1 && (
                <div className={`absolute left-[calc(50%+14px)] top-3.5 w-[calc(100%-28px)] h-0.5 z-0 ${
                  idx < currentStep ? 'bg-blue-600' : 'bg-[#E6EEFB]'
                }`} />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row gap-4 min-h-0">
        {/* Main Workspace */}
        <div className="flex-1 flex flex-col gap-4">
          <div className="flex-1 bg-white rounded-3xl border border-[#E6EEFB] shadow-sm flex flex-col p-8 sm:p-10 relative overflow-hidden">
             {/* Background heart pattern */}
             <Heart className="absolute -right-20 -top-20 text-blue-50/50 w-[400px] h-[400px]" strokeWidth={0.5} />
             
             <div className="relative z-10 flex flex-col h-full">
               <div className="flex items-center justify-between mb-12">
                 <div className="flex items-center gap-4">
                   <div className="text-xl font-bold text-[#0F6BFF] bg-blue-50 w-12 h-12 rounded-2xl flex items-center justify-center">0{currentQuestion}</div>
                   <div className="text-[#6B7893] text-sm font-bold uppercase tracking-widest">/ 0{phq9Questions.length} 题</div>
                 </div>
                 <div className="flex-1 h-2 bg-blue-50 rounded-full mx-10 overflow-hidden">
                   <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${(currentQuestion / phq9Questions.length) * 100}%` }}
                    className="h-full bg-blue-600 rounded-full shadow-[0_0_12px_rgba(15,107,255,0.3)]"
                   />
                 </div>
                 <div className="text-[#0F6BFF] font-bold">{Math.round((currentQuestion / phq9Questions.length) * 100)}%</div>
               </div>

               <div className="flex-1 flex flex-col items-center justify-center max-w-2xl mx-auto w-full text-center">
                 <AnimatePresence mode="wait">
                   <motion.h2 
                    key={currentQuestion}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 1.05 }}
                    className="text-2xl sm:text-3xl font-extrabold text-[#172033] leading-snug mb-8 sm:mb-12"
                   >
                     {currentQData.text}？
                   </motion.h2>
                 </AnimatePresence>

                 <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
                    {currentQData.options.map((option, idx) => (
                      <button
                        key={idx}
                        onClick={() => setSelectedOption(option.value)}
                        className={`h-16 sm:h-20 p-4 rounded-2xl border-2 transition-all duration-300 relative group active:scale-[0.98] ${
                          selectedOption === option.value 
                            ? 'border-[#0F6BFF] bg-blue-50 shadow-md shadow-blue-900/5' 
                            : 'border-[#E6EEFB] hover:border-blue-200 bg-white hover:bg-[#F5F8FF]/50'
                        }`}
                      >
                         <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110 ${option.colorClass}`}>
                               {idx === 0 && <span className="text-lg">😊</span>}
                               {idx === 1 && <span className="text-lg">🙂</span>}
                               {idx === 2 && <span className="text-lg">😐</span>}
                               {idx === 3 && <span className="text-lg">🙁</span>}
                            </div>
                            <span className="text-sm sm:text-base font-bold text-[#172033]">{option.label}</span>
                         </div>
                         {selectedOption === option.value && (
                            <motion.div 
                              layoutId="selection-check"
                              className="absolute top-2 right-2 w-5 h-5 bg-[#0F6BFF] rounded-full flex items-center justify-center text-white"
                            >
                              <span className="text-[10px] font-bold">✓</span>
                            </motion.div>
                         )}
                      </button>
                    ))}
                 </div>
               </div>
             </div>
          </div>

          {/* Action Bar */}
          <div className="h-24 bg-white rounded-3xl border border-[#E6EEFB] shadow-sm flex items-center justify-between px-8 relative overflow-hidden">
             <div className="flex items-center gap-3 z-10 w-40">
               <button 
                disabled={currentQuestion === 1}
                onClick={() => setCurrentQuestion(q => Math.max(1, q - 1))}
                className="h-10 px-4 border border-[#E6EEFB] bg-white text-[#6B7893] text-xs font-bold rounded-xl hover:bg-gray-50 flex items-center gap-1 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
               >
                 <ChevronLeft size={16} />
                 上题
               </button>
             </div>

             <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 flex flex-col items-center">
                <button className="w-14 h-14 rounded-full bg-[#0F6BFF] shadow-lg shadow-blue-500/20 flex items-center justify-center text-white ring-4 ring-blue-50 hover:scale-105 transition-all">
                   <Mic size={24} />
                </button>
             </div>

             <div className="flex items-center gap-3 z-10 w-40 justify-end">
               <button 
                onClick={handleNext}
                disabled={selectedOption === null}
                className="h-12 px-6 bg-[#0F6BFF] text-white text-xs font-bold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 hover:translate-x-1 transition-all disabled:opacity-50 disabled:grayscale"
               >
                 下题
                 <ChevronRight size={18} />
               </button>
             </div>
          </div>
        </div>

        {/* Right Monitoring Sidebar */}
        <div className="w-[320px] space-y-6 flex flex-col min-h-0">
           {/* Real-time Video Small */}
           <div className="bg-white rounded-3xl p-5 shadow-sm border border-[#E6EEFB] relative overflow-hidden">
              <div className="flex justify-between items-center mb-3">
                 <h3 className="text-xs font-bold text-[#172033] flex items-center gap-2">
                    实时视频
                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                 </h3>
                 <span className="text-[10px] text-[#6B7893] font-bold uppercase">Live</span>
              </div>
              
              <div className="aspect-video bg-slate-100 rounded-xl overflow-hidden relative group">
                <img 
                  src="https://images.unsplash.com/photo-1544005313-94ddf0286df2??w=400&h=300&fit=crop" 
                  alt="User" 
                  className="w-full h-full object-cover"
                />
                <button className="absolute top-2 right-2 w-7 h-7 bg-black/30 backdrop-blur-md rounded-lg flex items-center justify-center text-white opacity-0 group-hover:opacity-100 transition-all">
                   <Maximize2 size={12} />
                </button>
              </div>

              <div className="mt-3 flex items-center justify-center gap-2 bg-[#F5F8FF] py-2 rounded-xl border border-blue-50">
                 <Video size={14} className="text-[#0F6BFF]" />
                 <span className="text-[10px] font-bold text-[#172033]">多模态数据实时采集已开启</span>
              </div>
           </div>

           {/* Multimodal Status */}
           <div className="bg-white rounded-3xl p-5 shadow-sm border border-[#E6EEFB] flex-1 overflow-auto no-scrollbar">
              <div className="flex justify-between items-center mb-6">
                 <h3 className="text-xs font-bold text-[#172033] flex items-center gap-2">
                   多模态数据采集
                 </h3>
                 <div className="flex items-center gap-1">
                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                    <span className="text-[9px] text-emerald-500 font-bold uppercase tracking-wider">实时采集中</span>
                 </div>
              </div>

              <div className="space-y-4">
                 {multimodalStatuses.map((s, idx) => (
                   <div key={s.id} className="space-y-2">
                      <div className="flex justify-between items-center px-1">
                         <div className="text-[10px] font-bold text-[#172033] flex items-center gap-2">
                            <span className="w-4 h-4 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-[#0F6BFF] text-[8px]">{idx + 1}</span>
                            {s.label}
                         </div>
                         <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-full ${
                           s.status === 'analyzing' ? 'text-blue-500 bg-blue-50' : 'text-emerald-500 bg-emerald-50'
                         }`}>
                           {s.status === 'analyzing' ? '分析中' : '正常'}
                         </span>
                      </div>
                      <div className="h-6 flex items-center gap-1">
                         {Array.from({ length: 24 }).map((_, i) => (
                           <motion.div 
                            key={i}
                            animate={{ 
                              height: s.status === 'analyzing' 
                                ? [4, Math.random() * 8 + 4, 4] 
                                : [4, (i % 6 + 4) * 1.5, 4] 
                            }}
                            transition={{ repeat: Infinity, duration: 1, delay: i * 0.05 }}
                            className={`w-[3px] rounded-full ${
                              s.status === 'analyzing' ? 'bg-blue-300 opacity-40' : 'bg-[#0F6BFF]'
                            }`}
                           />
                         ))}
                      </div>
                   </div>
                 ))}
                 
                 <div className="pt-4 mt-4 border-t border-gray-50 grid grid-cols-2 gap-3">
                    <div className="p-3 bg-gray-50/50 rounded-2xl flex flex-col gap-1">
                       <span className="text-[8px] font-bold text-[#6B7893] uppercase">问诊用时</span>
                       <div className="flex items-center gap-2">
                         <Timer size={14} className="text-[#0F6BFF]" />
                         <span className="text-sm font-bold text-[#172033]">00:15:32</span>
                       </div>
                    </div>
                    <div className="p-3 bg-gray-50/50 rounded-2xl flex flex-col gap-1">
                       <span className="text-[8px] font-bold text-[#6B7893] uppercase">由于问诊安全</span>
                       <div className="flex items-center gap-2">
                         <Shield size={14} className="text-emerald-500" />
                         <span className="text-xs font-bold text-[#172033]">加密中</span>
                       </div>
                    </div>
                 </div>
              </div>
           </div>

           {/* Security Footer */}
           <div className="bg-[#F5F8FF] border border-[#E6EEFB] rounded-2xl p-4 flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center text-blue-600 shadow-sm">
                 <Shield size={16} />
              </div>
              <div className="flex-1">
                 <p className="text-[9px] text-[#6B7893] leading-relaxed">您的数据受《个人信息保护法》严格保护，加密传输仅用于本次门诊评估。</p>
              </div>
              <div className="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center">
                 <span className="text-blue-600 font-bold text-[8px] underline cursor-help">i</span>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
};

export default AssessmentPage;
