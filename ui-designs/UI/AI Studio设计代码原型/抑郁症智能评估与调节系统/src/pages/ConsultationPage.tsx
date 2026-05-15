import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { ConsultationLayout } from "../layouts";
import { mockConsultationService } from "../services/consultationService";
import { ConsultationState, MultimodalData } from "../types/consultation";

import { ConsultationProgress } from "./components/ConsultationProgress";
import { CameraPreview } from "./components/CameraPreview";
import { DraggableMessagePanel } from "./components/DraggableMessagePanel";
import { FloatingControlBar } from "./components/FloatingControlBar";
import { MultimodalPanel } from "./components/MultimodalPanel";
import { cn } from "../lib/utils";

export default function ConsultationPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const sessionId = location.state?.sessionId || "mock_session";

  const [isOpen, setIsOpen] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [state, setState] = useState<ConsultationState | null>(null);
  const [multiData, setMultiData] = useState<MultimodalData | null>(null);
  const [dhState, setDhState] = useState<'idle' | 'speaking'>('idle');

  // Load initial state
  useEffect(() => {
    mockConsultationService.getState(sessionId).then(res => {
      setState(res);
    });
  }, [sessionId]);

  // Polling multimodal data when panel is open
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isOpen) {
      mockConsultationService.getMultimodalData(sessionId).then(setMultiData);
      interval = setInterval(() => {
        mockConsultationService.getMultimodalData(sessionId).then(setMultiData);
      }, 2500);
    }
    return () => clearInterval(interval);
  }, [isOpen, sessionId]);

  const handleToggleRecord = async () => {
    if (isRecording) {
      // Stop recording and send message
      setIsRecording(false);
      if (state) {
        // Simulate sending a generic hardcoded user transcript just for UI flow
        const response = await mockConsultationService.sendMessage(sessionId, "我最近感觉压力有点大");
        setState({
          ...state,
          currentStep: response.currentStep,
          assistantMessage: response.assistantMessage
        });
        setDhState(response.digitalHumanState);
        
        // Return to idle after a few seconds simulator
        setTimeout(() => setDhState('idle'), 4000);
      }
    } else {
      setIsRecording(true);
    }
  };

  const handleEnd = async () => {
    await mockConsultationService.endConsultation(sessionId);
    navigate("/scale-questionnaire", { state: { sessionId } });
  };

  if (!state) {
    return (
      <ConsultationLayout title="智能评估">
        <div className="w-full h-full flex items-center justify-center text-slate-500">
           正在初始化问诊环境...
        </div>
      </ConsultationLayout>
    );
  }

  return (
    <ConsultationLayout backgroundImage="/bg.png" title="智能评估">
      
      {/* Progress Bar (Fixed top center) */}
      <div className="absolute top-0 inset-x-0 z-50 pointer-events-none">
        <div className="pointer-events-auto">
          <ConsultationProgress currentStep={state.currentStep} />
        </div>
      </div>
      
      <div className="flex w-full h-full relative z-10 bg-transparent pt-8 overflow-hidden [perspective:2000px]">
        
        {/* Left Side: Digital Human & Controls */}
        <div 
          className="flex-1 relative h-full flex flex-col items-center transition-all duration-[800ms] min-h-0 perspective-[1200px]"
          style={{ marginRight: isOpen ? 'min(45vw, 650px)' : '0px' }}
        >
          {/* Digital Human Image/Video Container */}
          <div className="flex-1 w-full max-w-[1200px] mx-auto flex flex-col items-center justify-end relative mt-10 z-10 pointer-events-none">
             {/* Empty state or minimal glow ring for the "Digital Human" spot */}
             <div className={`w-64 h-64 md:w-96 md:h-96 rounded-full mb-12 flex items-center justify-center transition-all duration-300 pointer-events-auto ${dhState === 'speaking' ? 'bg-primary-400/20 shadow-[0_0_80px_rgba(59,130,246,0.3)] animate-pulse' : 'bg-primary-100/10 shadow-[0_0_50px_rgba(59,130,246,0.1)]'}`}>
               <div className="w-1/2 h-1/2 rounded-full border-[1PX] border-primary-200/50 flex items-center justify-center">
                 <div className="w-1/2 h-1/2 rounded-full border-[1PX] border-primary-300/30"></div>
               </div>
             </div>
             
             <div className="absolute bottom-1/4 w-[80%] h-[2px] bg-gradient-to-r from-transparent via-primary-300/40 to-transparent"></div>
          </div>

          {/* Floating UI Container at the bottom */}
          <div className="absolute bottom-4 md:bottom-5 inset-x-0 z-20 flex flex-col items-center w-full gap-[10px] pb-0 pointer-events-auto shadow-sm">
            <FloatingControlBar 
              isRecording={isRecording} 
              onToggleRecord={handleToggleRecord} 
              onEnd={handleEnd}
            />
          </div>

          <div className="absolute left-[5%] lg:left-[10%] top-1/2 -translate-y-[40%] z-[100] pointer-events-none w-[240px] sm:w-[280px] flex items-center justify-center">
            <DraggableMessagePanel message={state.assistantMessage} />
          </div>
          
        </div>

        {/* Edge Toggle Button */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            "absolute top-1/2 -translate-y-1/2 z-30 transition-all duration-[800ms] flex flex-col items-center justify-center gap-1 bg-white/70 backdrop-blur-xl shadow-[0_4px_20px_rgba(59,130,246,0.15)] hover:text-primary-600 pointer-events-auto",
            isOpen 
              ? "translate-x-1/2 rounded-full w-8 h-16 border border-white/80" 
              : "right-0 rounded-l-xl w-8 py-4 border border-r-0 border-white/80 pr-0.5 hover:-translate-x-1"
          )}
          style={isOpen ? { right: 'min(45vw, 650px)' } : undefined}
        >
          {!isOpen ? (
            <>
              <span className="text-[11px] font-bold tracking-widest px-0.5 text-slate-600 mb-1" style={{ writingMode: 'vertical-rl' }}>实时结果</span>
              <ChevronLeft className="w-5 h-5 text-slate-500" />
            </>
          ) : (
            <ChevronRight className="w-5 h-5 text-slate-500" />
          )}
        </button>

        {/* Right Side: Multimodal Panel */}
        <div 
          className={cn(
             "absolute top-[2%] bottom-[2%] z-20 transition-all duration-[800ms] pointer-events-auto origin-right w-[45vw] max-w-[650px]",
             isOpen ? "right-0 opacity-100" : "-right-[600px] opacity-0"
          )}
          style={isOpen ? { transform: "rotateY(-15deg)" } : undefined}
        >
          {/* The actual floating card */}
          <div className="absolute inset-0 w-full h-full">
            <div className="w-full h-full bg-slate-900/10 transition-all duration-500 backdrop-blur-md rounded-3xl border border-indigo-400/60 shadow-[0_0_40px_rgba(99,102,241,0.6),inset_0_0_20px_rgba(165,180,252,0.4)] overflow-hidden flex flex-col relative z-30 ring-1 ring-indigo-400/30">
              <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-indigo-500/5 to-transparent pointer-events-none"></div>
              <div className="w-full h-full flex flex-col overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent relative z-10"> 
                 <div className="w-full shrink-0">
                   <MultimodalPanel data={multiData} onClose={() => setIsOpen(false)} />
                 </div>
              </div>
            </div>
          </div>
        </div>

        <div className={`absolute transition-all duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)] z-40 ${isOpen ? 'opacity-0 scale-95 pointer-events-none' : 'opacity-100 scale-100'} right-4 md:right-8 top-4 md:top-6`}>
          <CameraPreview 
            className="w-[25vw] min-w-[160px] max-w-[260px] aspect-[4/3] rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.4)] border border-white/20 ml-auto" 
          />
        </div>

      </div>
    </ConsultationLayout>
  );
}
