import React, { useState, useEffect } from 'react';
import { 
  Play, Pause, ChevronRight, Mic, Video, Maximize2, Volume2, 
  Settings, MoreHorizontal, Shield, Info, Activity, Clock
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { consultationSteps, emotionMetrics, mockUser } from '../mockData';

interface ConsultationPageProps {
  onComplete: () => void;
}

const ConsultationPage: React.FC<ConsultationPageProps> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(2);
  const [isRecording, setIsRecording] = useState(false);
  const [showHighRisk, setShowHighRisk] = useState(false);
  const [messages, setMessages] = useState([
    { id: 1, role: 'ai', text: '您好，我是您的数字医生小雨。接下来我会和您聊一聊近期的情绪状况，请您放松心情，如实回答。', time: '10:24:36' },
    { id: 2, role: 'ai', text: '最近两周，您的情绪状态怎么样？', time: '10:24:40' }
  ]);

  const handleNext = () => {
    if (currentStep < 6) {
      setCurrentStep(currentStep + 1);
    } else {
      onComplete();
    }
  };

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Step Indicator */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#E6EEFB] flex items-center justify-between">
        <div className="flex items-center gap-6 flex-1 px-4">
          {consultationSteps.map((step, idx) => (
            <div key={step.id} className="relative flex flex-col items-center gap-1 group flex-1">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-[10px] z-10 transition-all duration-300 ${
                step.id < currentStep ? 'bg-blue-600 text-white' : 
                step.id === currentStep ? 'bg-blue-600 text-white ring-4 ring-blue-50' : 
                'bg-[#F5F8FF] text-[#6B7893]'
              }`}>
                {step.id < currentStep ? '✓' : step.id}
              </div>
              <span className={`text-[10px] font-bold transition-colors ${step.id === currentStep ? 'text-[#172033]' : 'text-[#6B7893]'}`}>
                {step.label}
              </span>
              
              {idx < consultationSteps.length - 1 && (
                <div className={`absolute left-[calc(50%+14px)] top-3.5 w-[calc(100%-28px)] h-0.5 z-0 ${
                  step.id < currentStep ? 'bg-blue-600' : 'bg-[#E6EEFB]'
                }`} />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row gap-4 min-h-0">
        {/* Main Workspace */}
        <div className="flex-1 flex flex-col gap-4 min-w-0">
          <div className="flex-1 flex gap-4 min-h-0">
            {/* AI Avatar Panel */}
            <div className="w-[45%] bg-white rounded-3xl border border-[#E6EEFB] overflow-hidden relative shadow-sm flex flex-col">
              <div className="absolute top-4 left-4 z-20 flex items-center gap-2 px-2.5 py-1 bg-black/30 backdrop-blur-md rounded-full border border-white/20">
                 <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                 <span className="text-white text-[9px] font-bold">AI 数字医生</span>
              </div>

              <div className="absolute top-4 right-4 z-20 flex gap-2">
                <button className="w-8 h-8 rounded-full bg-black/30 backdrop-blur-md border border-white/20 flex items-center justify-center text-white hover:bg-black/50 transition-all">
                  <Maximize2 size={14} />
                </button>
                <button className="w-8 h-8 rounded-full bg-black/30 backdrop-blur-md border border-white/20 flex items-center justify-center text-white hover:bg-black/50 transition-all">
                  <Volume2 size={14} />
                </button>
                <button className="w-8 h-8 rounded-full bg-black/30 backdrop-blur-md border border-white/20 flex items-center justify-center text-white hover:bg-black/50 transition-all">
                  <Settings size={14} />
                </button>
              </div>

              <div className="flex-1 bg-slate-900 overflow-hidden relative flex items-center justify-center">
                 <img 
                  src="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=800&h=1200&fit=crop" 
                  alt="AI Avatar" 
                  className="w-full h-full object-cover opacity-80"
                 />
                 
                 {/* Voice Waveform Overlay on Avatar */}
                 <div className="absolute bottom-10 left-1/2 -translate-x-1/2 w-48 h-8 flex items-end justify-center gap-1">
                    {[1,2,3,4,3,2,1,2,3,4,5,4,3].map((h, i) => (
                      <motion.div 
                        key={i}
                        animate={{ height: [h*4, h*8, h*4] }}
                        transition={{ repeat: Infinity, duration: 1, delay: i * 0.1 }}
                        className="w-1 bg-[#0F6BFF] rounded-full"
                      />
                    ))}
                 </div>
              </div>

              {/* Subtitles Area */}
              <div className="h-28 bg-[#172033] p-6 flex flex-col justify-center">
                 <p className="text-white/90 text-sm leading-relaxed text-center font-medium italic">
                   “您好，我是您的数字医生小雨。接下来我会和您聊一聊近期的情绪状况，请您放松心情，如实回答。”
                 </p>
                 <div className="mt-2 flex justify-center items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full" />
                    <span className="text-emerald-500 text-[10px] font-bold uppercase tracking-widest">语音连接正常</span>
                 </div>
              </div>
            </div>

            {/* Chat Panel */}
            <div className="flex-1 bg-white rounded-3xl border border-[#E6EEFB] shadow-sm flex flex-col overflow-hidden">
               <div className="h-10 border-b border-[#E6EEFB] flex bg-gray-50/30">
                  {['问诊对话', '风险排查', '问诊笔记'].map((tab, i) => (
                    <button 
                      key={tab}
                      className={`flex-1 text-[10px] font-bold transition-all relative ${i === 0 ? 'text-[#0F6BFF] bg-white' : 'text-[#6B7893]'}`}
                    >
                      {tab}
                      {i === 0 && <div className="absolute top-0 left-0 right-0 h-1 bg-[#0F6BFF]" />}
                    </button>
                  ))}
               </div>

               <div className="flex-1 p-4 overflow-auto space-y-4">
                 {messages.map((msg) => (
                   <div key={msg.id} className={`flex gap-3 ${msg.role === 'ai' ? 'flex-row' : 'flex-row-reverse'}`}>
                      <div className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center overflow-hidden border ${msg.role === 'ai' ? 'bg-blue-50 border-blue-100' : 'bg-white border-[#E6EEFB]'}`}>
                        {msg.role === 'ai' ? (
                          <div className="w-4 h-4 bg-blue-600 rounded-sm rotate-45" />
                        ) : (
                          <img src={mockUser.avatar} className="w-full h-full object-cover" alt="Me" />
                        )}
                      </div>
                      <div className="space-y-1">
                        <div className={`p-3 rounded-xl text-[11px] leading-relaxed max-w-[280px] ${msg.role === 'ai' ? 'bg-blue-50 text-blue-900 font-medium' : 'bg-[#172033] text-white'}`}>
                          {msg.text}
                        </div>
                        <div className={`text-[8px] text-[#6B7893] ${msg.role === 'ai' ? '' : 'text-right'}`}>{msg.time}</div>
                      </div>
                   </div>
                 ))}

                 {isRecording && (
                    <motion.div 
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="border-2 border-dashed border-blue-100 rounded-2xl p-4 bg-blue-50/50"
                    >
                       <div className="flex justify-between items-center mb-3">
                          <div className="flex items-center gap-2">
                             <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                             <span className="text-[9px] font-bold text-[#0F6BFF] uppercase tracking-wider">实时语音识别</span>
                          </div>
                          <button className="text-[#6B7893] hover:text-rose-500 transition-colors">
                            <MoreHorizontal size={14} />
                          </button>
                       </div>
                       <p className="text-xs text-[#172033]/40 font-medium italic min-h-[30px]">
                          请按住下方按钮开始说话...
                       </p>
                    </motion.div>
                 )}
               </div>
            </div>
          </div>

          {/* Voice Control Bar */}
          <div className="h-24 bg-white rounded-3xl border border-[#E6EEFB] shadow-sm flex items-center justify-between px-8 relative overflow-hidden">
             <div className="flex items-center gap-3 z-10 w-40">
               <button className="w-10 h-10 rounded-full bg-white border border-[#E6EEFB] shadow-sm flex items-center justify-center text-[#6B7893] hover:bg-gray-50 transition-all active:scale-95">
                 <Pause size={16} />
               </button>
               <button className="h-10 px-3 rounded-full bg-white border border-blue-100 shadow-sm flex items-center gap-2 text-[#0F6BFF] text-[10px] font-bold hover:bg-blue-50 transition-all active:scale-95">
                 <MoreHorizontal size={16} />
                 重说
               </button>
             </div>

             <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
                <button 
                  onMouseDown={() => setIsRecording(true)}
                  onMouseUp={() => setIsRecording(false)}
                  onMouseLeave={() => setIsRecording(false)}
                  className={`w-16 h-16 rounded-full shadow-xl transition-all flex items-center justify-center ring-4 ${
                    isRecording 
                      ? 'bg-rose-500 ring-rose-100 scale-110 shadow-rose-200' 
                      : 'bg-[#0F6BFF] ring-blue-50 hover:scale-105 active:scale-95 shadow-blue-200'
                  }`}
                >
                  <Mic size={28} className="text-white" />
                </button>
             </div>

             <div className="flex items-center gap-3 z-10 w-40 justify-end">
               <button 
                onClick={handleNext}
                className="h-12 px-6 bg-[#0F6BFF] text-white text-xs font-bold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 hover:translate-x-1 transition-all"
               >
                 下一步
                 <ChevronRight size={18} />
               </button>
             </div>
          </div>
        </div>

        {/* Right Monitoring Sidebar */}
        <div className="w-[280px] space-y-4 flex flex-col min-h-0 shrink-0">
           {/* Real-time Video Small */}
           <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#E6EEFB] relative overflow-hidden">
              <div className="flex justify-between items-center mb-2">
                 <h3 className="text-[10px] font-bold text-[#172033] flex items-center gap-1.5 uppercase">
                    实时监测
                    <div className="w-1 h-1 bg-emerald-500 rounded-full animate-pulse" />
                 </h3>
                 <span className="text-[8px] text-emerald-500 font-bold bg-emerald-50 px-2 py-0.5 rounded-full uppercase">Monitoring</span>
              </div>
              
              <div className="aspect-video bg-slate-100 rounded-xl overflow-hidden relative group">
                <img 
                  src="https://images.unsplash.com/photo-1531123897727-8f129e16fd3c?w=400&h=300&fit=crop" 
                  alt="User" 
                  className="w-full h-full object-cover"
                />
                <div className="absolute top-2 left-2 px-1.5 py-0.5 bg-black/40 rounded flex items-center gap-1">
                   <div className="w-1 h-1 bg-rose-500 rounded-full" />
                   <span className="text-[7px] text-white font-bold uppercase">Rec</span>
                </div>
              </div>

              <div className="mt-2 flex items-center justify-between">
                 <div className="flex items-center gap-1.5">
                   <Video size={12} className="text-[#0F6BFF]" />
                   <span className="text-[9px] font-bold text-[#6B7893]">摄像头接入</span>
                 </div>
                 <button className="p-1 bg-blue-50 rounded-lg text-blue-600 hover:bg-blue-100 transition-colors">
                   <Maximize2 size={10} />
                 </button>
              </div>
           </div>

           {/* Session Progress */}
           <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#E6EEFB]">
              <div className="flex justify-between items-center mb-3">
                 <h3 className="text-[10px] font-bold text-[#172033] flex items-center gap-1.5 uppercase">
                   进度
                 </h3>
                 <span className="text-[9px] text-blue-600 font-bold uppercase">{currentStep} / 6</span>
              </div>
              <div className="h-1.5 bg-[#F5F8FF] rounded-full overflow-hidden mb-3">
                 <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${(currentStep/6)*100}%` }}
                  className="h-full bg-blue-600 rounded-full"
                 />
              </div>
              <p className="text-[9px] font-bold text-[#6B7893] mb-0.5 uppercase tracking-tight">当前阶段</p>
              <p className="text-xs font-bold text-[#172033] line-clamp-1">{consultationSteps[currentStep-1]?.label}</p>
           </div>

           {/* Emotion Metrics */}
           <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#E6EEFB] shrink-0">
              <div className="flex justify-between items-center mb-3">
                 <h3 className="text-[10px] font-bold text-[#172033] uppercase">
                   实时情绪
                 </h3>
                 <div className="flex items-center gap-1">
                    <div className="w-1 h-1 bg-emerald-500 rounded-full" />
                    <span className="text-[8px] text-[#6B7893] font-bold uppercase">实时</span>
                 </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                 {emotionMetrics.map((m) => (
                   <div key={m.id} className="p-2 bg-gray-50/50 rounded-xl border border-gray-100">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-[8px] font-bold text-[#6B7893] line-clamp-1">{m.label}</span>
                        <div 
                          className="w-1 h-1 rounded-full" 
                          style={{ backgroundColor: m.color }} 
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-[#172033]">{m.statusText}</span>
                        <span className="text-[8px] text-[#6B7893] font-mono">{m.value}</span>
                      </div>
                   </div>
                 ))}
              </div>
           </div>

           {/* Consultation Tips/Safety */}
           <div className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-3xl p-6 text-white shadow-lg shadow-blue-900/20 relative overflow-hidden flex-1 flex flex-col justify-center">
              {/* Pattern */}
              <div className="absolute top-0 right-0 w-24 h-24 bg-white/10 rounded-full -mr-12 -mt-12" />
              <div className="absolute bottom-0 left-0 w-16 h-16 bg-blue-400/20 rounded-full -ml-8 -mb-8" />
              
              <div className="flex items-center gap-3 mb-4 relative z-10">
                 <div className="w-10 h-10 bg-white/20 backdrop-blur-md rounded-xl flex items-center justify-center">
                    <Shield size={20} />
                 </div>
                 <h3 className="font-bold">安全建议</h3>
              </div>
              <ul className="space-y-4 relative z-10">
                 {[
                   { icon: Info, text: '如实表达您的当下感受' },
                   { icon: Activity, text: '如果您感到极度不适，请点击暂停' },
                   { icon: Shield, text: '该数据仅由于医疗辅助分析' },
                   { icon: Clock, text: '预计剩余时长：15-20 分钟' }
                 ].map((item, i) => (
                   <li key={i} className="flex gap-3 items-center">
                      <item.icon size={14} className="text-blue-300 shrink-0" />
                      <p className="text-xs text-blue-100 leading-tight">{item.text}</p>
                   </li>
                 ))}
              </ul>
           </div>
        </div>
      </div>
    </div>
  );
};

export default ConsultationPage;
