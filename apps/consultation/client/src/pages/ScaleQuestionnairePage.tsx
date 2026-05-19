import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight, Info } from "lucide-react";

import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { ConsultationStatusPanel } from "../components/ConsultationStatusPanel";
import { ConsultationLayout } from "../layouts";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";
import { mockConsultationService } from "../services/consultationService";
import type { ConsultationSession } from "../types";

import { CameraPreview } from "../components/CameraPreview";
import { FloatingControlBar } from "../components/FloatingControlBar";
import { DraggableMessagePanel } from "../components/DraggableMessagePanel";
import { ConsultationProgress } from "../components/ConsultationProgress";

// Mock Scale Questions
const SCALE_QUESTIONS = [
  {
    id: 1,
    text: "做事时提不起劲或没有兴趣的情况有多频繁？",
    options: [
      { label: "A", text: "完全没有", subtext: "0天" },
      { label: "B", text: "几天", subtext: "1-2天" },
      { label: "C", text: "一半以上天数", subtext: "3-6天" },
      { label: "D", text: "几乎每天", subtext: "7-9天" },
    ]
  },
  {
    id: 2,
    text: "感到心情低落、沮丧或绝望的情况有多频繁？",
    options: [
      { label: "A", text: "完全没有", subtext: "0天" },
      { label: "B", text: "几天", subtext: "1-2天" },
      { label: "C", text: "一半以上天数", subtext: "3-6天" },
      { label: "D", text: "几乎每天", subtext: "7-9天" },
    ]
  },
  {
    id: 3,
    text: "入睡困难、睡不安稳或睡眠过多？",
    options: [
      { label: "A", text: "完全没有", subtext: "0天" },
      { label: "B", text: "几天", subtext: "1-2天" },
      { label: "C", text: "一半以上天数", subtext: "3-6天" },
      { label: "D", text: "几乎每天", subtext: "7-9天" },
    ]
  }
];

export default function ScaleQuestionnairePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { state, actions } = useConsultationAppContext();
  const sessionId = location.state?.sessionId || "mock_session";

  const [isOpen, setIsOpen] = useState(false);
  const [isScaleOpen, setIsScaleOpen] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [dhState, setDhState] = useState<'idle' | 'speaking'>('idle');
  
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [assistantMessage, setAssistantMessage] = useState("您好，我是您的数字人医生。接下来，我们将通过量表评估了解您的心理健康状况。请根据最近2周的实际感受作答。");

  // Load initial state
  useEffect(() => {
    // We can simulate fetching initial status
    setDhState('speaking');
    setTimeout(() => setDhState('idle'), 4000);
  }, []);

  const handleToggleRecord = async () => {
    if (isRecording) {
      setIsRecording(false);
      // specific voice response for scale
      setAssistantMessage("我已记录您的语音反馈。可以继续完成量表。");
      setDhState('speaking');
      setTimeout(() => setDhState('idle'), 3000);
    } else {
      setIsRecording(true);
    }
  };

  const handleEnd = async () => {
    await mockConsultationService.endConsultation(sessionId);
    navigate(APP_PATHS.result);
  };

  const currentQuestion = SCALE_QUESTIONS[currentQuestionIndex];
  const multimodalConsultation = useMemo<ConsultationSession>(() => {
    if (state.consultation) {
      return state.consultation;
    }

    const stageOrder = Math.min(4, Math.max(1, currentQuestionIndex + 1));
    return {
      session_id: sessionId,
      user_id: "assessment-preview-user",
      status: "waiting_user_input",
      workflow_id: "assessment-preview",
      current_prompt_key: `assessment-${currentQuestion.id}`,
      current_prompt_question_text: currentQuestion.text,
      current_prompt_subtitle_text: currentQuestion.text,
      current_stage: {
        stage_id: "assessment",
        stage_label: "量表评估",
        stage_order: stageOrder,
        total_stages: 4,
      },
      current_question_item: {
        question_key: `assessment-${currentQuestion.id}`,
        stage_id: "assessment",
        stage_label: "量表评估",
        stage_order: stageOrder,
        order: currentQuestion.id,
        node_id: `assessment-${currentQuestion.id}`,
        question_text: currentQuestion.text,
        subtitle_text: currentQuestion.text,
        response_required: true,
      },
    };
  }, [currentQuestion.id, currentQuestion.text, currentQuestionIndex, sessionId, state.consultation]);

  async function handleRefresh() {
    await actions.refreshConsultation();
  }

  const handleOptionSelect = (optionIndex: number) => {
    if (currentQuestionIndex < SCALE_QUESTIONS.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setAssistantMessage(`您选择了 ${currentQuestion.options[optionIndex].label}。请看下一题。`);
      setDhState('speaking');
      setTimeout(() => setDhState('idle'), 2000);
    } else {
      setAssistantMessage("量表答题完毕，感谢您的配合。点击结束评估查看报告。");
      setDhState('speaking');
      setTimeout(() => setDhState('idle'), 3000);
    }
  };

  return (
    <ConsultationLayout backgroundImage="/4K.png" title="量表问诊">
      
      {/* Progress Bar (Fixed top center) */}
      <div className="absolute top-0 inset-x-0 z-50 pointer-events-none">
        <div className="pointer-events-auto">
          <ConsultationProgress currentStep={1} steps={['PHQ-9', 'SDS', 'SAS', '社会功能量表']} />
        </div>
      </div>
      
      <div 
        style={{
            '--scale-panel-width': 'clamp(260px, 22vw, 340px)',
            '--scale-panel-left': 'clamp(12px, 2vw, 32px)',
            '--scale-visual-width': 'calc(var(--scale-panel-width) * 0.966)', // cos(15deg)
            '--scale-total-offset': 'calc(var(--scale-panel-left) + var(--scale-visual-width))',
            perspective: '1200px'
        } as CSSProperties}
        className="flex w-full h-full relative z-10 bg-transparent overflow-hidden pt-8"
      >
        
        {/* Left Side: Digital Human & Controls */}
        <div 
          className={cn(
             "flex-1 relative h-full flex flex-col items-center transition-all duration-[800ms] min-h-0 perspective-[1200px]"
          )}
          style={{ 
             marginLeft: isScaleOpen ? 'var(--scale-total-offset)' : '0px',
             marginRight: isOpen ? (isScaleOpen ? 'min(40vw, 500px)' : 'min(44vw, 650px)') : '0px' 
          }}
        >
          
          {/* Digital Human Image/Video Container */}
          <div className="flex-1 w-full max-w-[1200px] mx-auto flex flex-col items-center justify-end relative mt-0 z-10 pointer-events-none">
             {/* Replace this with human image if exists, or keep empty state. In ConsultationPage we had minimal glow ring */}
             
             {/* Subtitle Message Square Area */}
             <div className="absolute right-[5%] lg:right-[12%] top-1/2 -translate-y-[40%] z-[100] pointer-events-none w-[240px] sm:w-[280px] flex items-center justify-center">
               <DraggableMessagePanel lines={[assistantMessage]} />
             </div>

             <div className={cn(
               "w-64 h-64 md:w-96 md:h-96 rounded-full mb-12 flex items-center justify-center transition-all duration-300 pointer-events-none",
               dhState === 'speaking' ? "bg-primary-400/20 shadow-[0_0_80px_rgba(59,130,246,0.3)] animate-pulse" : "bg-primary-100/10 shadow-[0_0_50px_rgba(59,130,246,0.1)]"
             )}>
               <div className="w-1/2 h-1/2 rounded-full border-[1PX] border-primary-200/50 flex items-center justify-center">
                 <div className="w-1/2 h-1/2 rounded-full border-[1PX] border-primary-300/30"></div>
               </div>
             </div>
             
             <div className="absolute bottom-1/4 w-[80%] h-[2px] bg-gradient-to-r from-transparent via-primary-300/40 to-transparent"></div>
          </div>

          {/* Floating Control Bar at the bottom center */}
          <div className="absolute bottom-4 md:bottom-5 inset-x-0 z-20 flex flex-col items-center w-full pb-0 pointer-events-auto">
            <FloatingControlBar 
              isRecording={isRecording} 
              onToggleRecord={handleToggleRecord} 
              onEnd={handleEnd}
            />
          </div>
          
        </div>

        {/* Scale Questionnaire Dashboard (Floating, tilted 15deg) */}
        <div className={cn(
           "absolute top-0 bottom-0 my-auto z-30 transition-all duration-[800ms] pointer-events-auto origin-left flex flex-col justify-center transform-gpu",
           isScaleOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )} style={{ 
            width: 'var(--scale-panel-width)',
            height: 'fit-content',
            maxHeight: '90vh',
            left: isScaleOpen ? 'var(--scale-panel-left)' : 'calc(-1 * var(--scale-panel-width) - 50px)',
            transform: isScaleOpen ? "rotateY(15deg)" : "rotateY(15deg) translateX(-20px)",
            containerType: 'inline-size'
        }}>
          <div className="w-full bg-slate-900/10 backdrop-blur-md border border-indigo-400/60 rounded-[clamp(16px,4cqw,24px)] p-[clamp(16px,5cqw,24px)] shadow-[0_0_30px_rgba(99,102,241,0.6),inset_0_0_20px_rgba(165,180,252,0.4)] flex flex-col relative overflow-hidden ring-1 ring-indigo-400/30 shrink-0 transform-gpu">
             {/* Glow effects */}
            <div className="absolute top-0 inset-x-0 h-[100px] bg-gradient-to-b from-primary-500/20 to-transparent pointer-events-none"></div>
            <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent pointer-events-none"></div>

            {/* Header */}
            <div className="flex items-center gap-3 mb-[clamp(16px,4cqw,24px)] relative z-10 shrink-0">
              <div className="bg-primary-500/20 border border-primary-400/30 text-primary-200 px-[clamp(8px,2cqw,12px)] py-[clamp(4px,1cqw,6px)] rounded-full text-[clamp(12px,3cqw,14px)] font-semibold flex items-center shrink-0">
                PHQ-9
              </div>
              <span className="text-slate-300 text-[clamp(12px,3cqw,14px)] font-medium truncate">第 {currentQuestionIndex + 1}/{SCALE_QUESTIONS.length} 题</span>
            </div>

            {/* Question */}
            <h3 className="text-slate-50 text-[clamp(16px,4.5cqw,22px)] font-medium leading-relaxed mb-[clamp(16px,4cqw,24px)] relative z-10 shrink-0">
              {currentQuestion.text}
            </h3>

            {/* Options */}
            <div className="flex flex-col gap-[clamp(8px,2cqw,12px)] relative z-10 shrink-0 overflow-y-auto overflow-x-hidden min-h-0 pr-1 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
              {currentQuestion.options.map((opt, idx) => (
                <button 
                  key={idx}
                  onClick={() => handleOptionSelect(idx)}
                  className="w-full shrink-0 group relative text-left bg-white/5 hover:bg-primary-500/20 border border-white/10 hover:border-primary-400/50 rounded-[clamp(12px,3cqw,16px)] p-[clamp(12px,3cqw,16px)] transition-all duration-[300ms] flex items-center gap-[clamp(12px,3cqw,16px)] focus:outline-none"
                >
                  <div className="w-[clamp(32px,8cqw,40px)] h-[clamp(32px,8cqw,40px)] shrink-0 bg-white/10 group-hover:bg-primary-500/30 rounded-[clamp(8px,2cqw,12px)] flex items-center justify-center text-white font-semibold text-[clamp(14px,3.5cqw,18px)] transition-colors border border-white/5">
                    {opt.label}
                  </div>
                  <div className="flex-1 flex flex-col overflow-hidden">
                    <span className="text-slate-200 group-hover:text-white text-[clamp(14px,3.5cqw,16px)] transition-colors truncate">{opt.text}</span>
                    <span className="text-slate-400 group-hover:text-primary-200 text-[clamp(11px,2.5cqw,12px)] transition-colors truncate">{opt.subtext}</span>
                  </div>
                  {/* Active highlight */}
                  <div className="absolute inset-0 bg-gradient-to-r from-primary-500/0 via-primary-500/0 to-primary-500/10 opacity-0 group-hover:opacity-100 transition-opacity rounded-[clamp(12px,3cqw,16px)] pointer-events-none"></div>
                </button>
              ))}
            </div>

            {/* Footer text */}
            <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-center gap-2 text-slate-400 text-[clamp(11px,2.5cqw,12px)] relative z-10 shrink-0">
              <Info size={14} className="opacity-70 shrink-0" />
              <span className="truncate">请选择符合您最近两周的情况</span>
            </div>
          </div>
        </div>

        {/* Edge Toggle Buttons */}
        <button
          onClick={() => setIsScaleOpen(!isScaleOpen)}
          className={cn(
            "absolute top-1/2 -translate-y-1/2 z-30 transition-all duration-[800ms] flex flex-col items-center justify-center gap-1 bg-white/70 backdrop-blur-xl shadow-[0_4px_20px_rgba(59,130,246,0.15)] hover:text-primary-600 pointer-events-auto",
            isScaleOpen 
              ? "-translate-x-1/2 rounded-full w-8 h-16 border border-white/80" 
              : "left-0 rounded-r-xl w-8 py-4 border border-l-0 border-white/80 pl-0.5 hover:translate-x-1"
          )}
          style={{
             left: isScaleOpen ? 'var(--scale-total-offset)' : undefined
          }}
        >
          {!isScaleOpen ? (
            <>
              <ChevronRight className="w-5 h-5 text-slate-500" />
              <span className="text-[11px] font-bold tracking-widest px-0.5 text-slate-600 mt-1" style={{ writingMode: 'vertical-rl' }}>量表问诊</span>
            </>
          ) : (
            <ChevronLeft className="w-5 h-5 text-slate-500" />
          )}
        </button>

        <button
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            "absolute top-1/2 -translate-y-1/2 z-30 transition-all duration-[800ms] flex flex-col items-center justify-center gap-1 bg-white/70 backdrop-blur-xl shadow-[0_4px_20px_rgba(59,130,246,0.15)] hover:text-primary-600 pointer-events-auto",
            isOpen 
              ? "translate-x-1/2 rounded-full w-8 h-16 border border-white/80" 
              : "right-0 rounded-l-xl w-8 py-4 border border-r-0 border-white/80 pr-0.5 hover:-translate-x-1"
          )}
          style={isOpen ? { right: isScaleOpen ? 'min(40vw, 500px)' : 'min(44vw, 650px)' } : undefined}
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
             "absolute top-[2%] bottom-[2%] z-20 transition-all duration-[800ms] pointer-events-auto origin-right",
             isOpen ? "right-0 opacity-100" : "-right-[600px] opacity-0",
             isScaleOpen ? "w-[40vw] max-w-[500px]" : "w-[44vw] max-w-[650px]"
          )}
          style={isOpen ? { transform: "rotateY(-5deg)" } : undefined}
        >
          {/* The actual floating card */}
          <div className="absolute inset-0 w-full h-full">
            <div className="w-full h-full bg-slate-900/10 transition-all duration-500 backdrop-blur-md rounded-3xl border border-indigo-400/60 shadow-[0_0_40px_rgba(99,102,241,0.6),inset_0_0_20px_rgba(165,180,252,0.4)] overflow-hidden flex flex-col relative z-30 ring-1 ring-indigo-400/30">
              <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-indigo-500/5 to-transparent pointer-events-none"></div>
              <div className="w-full h-full flex flex-col overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent relative z-10"> 
                 <div className="w-full h-full min-h-0">
                   <ConsultationStatusPanel
                     consultation={multimodalConsultation}
                     onRefresh={handleRefresh}
                     refreshing={state.loading}
                     isRecording={isRecording}
                     className="h-full"
                   />
                 </div>
              </div>
            </div>
          </div>
        </div>

        {/* Floating Camera Preview */}
        <div className={`absolute transition-all duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)] z-40 ${isOpen ? 'opacity-0 scale-95 pointer-events-none' : 'opacity-100 scale-100'} right-4 md:right-8 top-4 md:top-6`}>
          <CameraPreview 
            className="w-[25vw] min-w-[160px] max-w-[260px] aspect-[4/3] rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.4)] border border-white/20 ml-auto" 
          />
        </div>

      </div>
    </ConsultationLayout>
  );
}
