import { useNavigate } from "react-router-dom";
import { ConsultationLayout } from "../layouts";
import { motion } from "motion/react";

export default function InterventionPage() {
  const navigate = useNavigate();

  const buttonVariants = {
    initial: { y: 0 },
    float: {
      y: [-5, 5, -5],
      transition: {
        duration: 4,
        repeat: Infinity,
        ease: "easeInOut"
      }
    },
    hover: {
      scale: 1.05,
      rotate: [-1, 1, -1, 0],
      transition: {
        rotate: {
          duration: 0.3,
          ease: "easeInOut"
        }
      }
    },
    tap: {
      scale: 0.95
    }
  };

  // 悬浮动态玻璃拟态星光果冻效果 (Floating dynamic glassmorphism starlight jelly effect)
  const renderGlassButton = (text: string, delay: number) => (
    <motion.button
      variants={buttonVariants}
      initial="initial"
      animate="float"
      whileHover="hover"
      whileTap="tap"
      style={{ animationDelay: `${delay}s` }}
      className="group relative flex items-center justify-center w-[220px] md:w-[260px] h-[52px] md:h-[60px] rounded-[24px] outline-none overflow-visible"
    >
      {/* Twinkling Stars (Starlight) */}
      <div className="absolute -inset-6 z-0 pointer-events-none opacity-50 group-hover:opacity-100 transition-opacity duration-500">
        <div className="absolute top-[10%] left-[10%] w-1.5 h-1.5 bg-white rounded-full shadow-[0_0_8px_rgba(255,255,255,0.8)] animate-[pulse_2s_ease-in-out_infinite]"></div>
        <div className="absolute top-[20%] right-[15%] w-1 h-1 bg-white rounded-full shadow-[0_0_5px_rgba(255,255,255,0.8)] animate-[pulse_1.5s_ease-in-out_infinite_0.3s]"></div>
        <div className="absolute bottom-[20%] left-[25%] w-2 h-2 bg-blue-100 rounded-full shadow-[0_0_10px_rgba(255,255,255,0.9)] animate-[pulse_2.5s_ease-in-out_infinite_0.7s]"></div>
        <div className="absolute bottom-[10%] right-[10%] w-1 h-1 bg-purple-100 rounded-full shadow-[0_0_8px_rgba(255,255,255,0.8)] animate-[pulse_1.8s_ease-in-out_infinite_0.5s]"></div>
        <div className="absolute top-[50%] left-[-10px] w-1.5 h-1.5 bg-white rounded-full shadow-[0_0_6px_rgba(255,255,255,0.8)] animate-[pulse_2.2s_ease-in-out_infinite_1.2s]"></div>
        <div className="absolute top-[80%] right-[-5px] w-1 h-1 bg-white rounded-full shadow-[0_0_4px_rgba(255,255,255,0.8)] animate-[pulse_1.7s_ease-in-out_infinite_0.9s]"></div>
      </div>

      {/* Outer Glow / Starlight effect */}
      <div className="absolute inset-0 rounded-[24px] bg-gradient-to-r from-blue-300 via-indigo-200 to-purple-300 opacity-0 group-hover:opacity-40 blur-xl transition-opacity duration-500 pointer-events-none z-10"></div>
      
      {/* Dynamic Glassmorphism Background */}
      <div className="absolute inset-0 rounded-[24px] bg-white/10 backdrop-blur-xl border border-white/30 shadow-[0_8px_32px_rgba(31,38,135,0.1),inset_0_4px_24px_rgba(255,255,255,0.2)] flex items-center justify-center overflow-hidden z-20">
        {/* Shimmer sweep */}
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite] pointer-events-none skew-x-12"></div>
        {/* Top edge glossy highlight */}
        <div className="absolute top-0 inset-x-4 h-[1px] bg-gradient-to-r from-transparent via-white/60 to-transparent"></div>
        {/* Subtle inner star glow on hover */}
        <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>

        <span className="text-white font-medium text-lg md:text-xl tracking-[0.2em] drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
          {text}
        </span>
      </div>
    </motion.button>
  );

  return (
    <ConsultationLayout backgroundImage="/TKbg.png" title="调节干预">
      <div className="w-full h-full relative overflow-hidden flex flex-col items-center justify-end pb-4 md:pb-6">
        
        {/* Background gradient overlay to make human and buttons stand out */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/40 pointer-events-none"></div>

        {/* Digital Human Image */}
        <div className="absolute inset-x-0 bottom-0 top-16 flex justify-center items-end pointer-events-none">
          <img 
            src="/SZR.png" 
            alt="AI Assistant" 
            className="h-[85%] max-w-none object-contain object-bottom pointer-events-auto filter drop-shadow-2xl"
          />
        </div>

        {/* Action Buttons */}
        <div className="w-full max-w-5xl px-6 relative z-10 flex flex-col md:flex-row items-center justify-center gap-6 md:gap-10 perspective-[1000px]">
          {renderGlassButton("看一段视频", 0)}
          {renderGlassButton("玩一个小游戏", 0.2)}
          {renderGlassButton("听一段故事", 0.4)}
        </div>
      </div>
    </ConsultationLayout>
  );
}
