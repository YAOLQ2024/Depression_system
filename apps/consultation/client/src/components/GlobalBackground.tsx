import { ReactNode } from "react";

export function GlobalBackground() {
  return (
    <div className="absolute inset-0 w-full h-full object-cover z-0 pointer-events-none overflow-hidden bg-[#f4f7fe]">
       {/* Breathing purple blue gradients */}
       <div className="absolute w-[80vw] h-[80vh] top-[10%] left-[-10%] bg-blue-400/20 rounded-full blur-[120px] mix-blend-multiply animate-[pulse_8s_ease-in-out_infinite]" />
       <div className="absolute w-[70vw] h-[70vh] bottom-[-10%] right-[-10%] bg-purple-400/20 rounded-full blur-[150px] mix-blend-multiply animate-[pulse_10s_ease-in-out_infinite_reverse]" />
       <div className="absolute w-[50vw] h-[50vh] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-indigo-300/10 rounded-full blur-[100px] mix-blend-multiply animate-[pulse_6s_ease-in-out_infinite]" />
       
       <svg className="absolute inset-0 w-full h-full opacity-60" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
         {/* Tech waves with stroke indigo-300 */}
         <path d="M-200,800 C400,900 600,200 1200,300 C1800,400 2000,800 2500,600" fill="none" stroke="rgba(99,102,241,0.2)" strokeWidth="3" filter="blur(2px)" />
         <path d="M-200,800 C400,900 600,200 1200,300 C1800,400 2000,800 2500,600" fill="none" stroke="rgba(99,102,241,0.4)" strokeWidth="1" />
         
         <path d="M-100,500 C300,600 400,700 1000,600 C1600,500 1800,-100 2400,200" fill="none" stroke="rgba(139,92,246,0.2)" strokeWidth="5" filter="blur(3px)" />
         <path d="M-100,500 C300,600 400,700 1000,600 C1600,500 1800,-100 2400,200" fill="none" stroke="rgba(139,92,246,0.4)" strokeWidth="1.5" />

         {/* Glowing brain element visible on left middle */}
         <g transform="translate(10vw, 30vh) scale(2.5)" opacity="0.6">
            <path d="M50 20 C60 10, 80 10, 90 20 C100 20, 110 30, 110 40 C120 40, 130 60, 120 80 C110 100, 90 110, 70 100 C60 110, 40 100, 30 80 C20 60, 30 40, 40 40 C40 30, 40 20, 50 20 Z" fill="none" stroke="url(#brainGrad)" strokeWidth="1.5" strokeDasharray="3 3"/>
            <path d="M55 35 L70 70 L85 45 M70 70 L45 65 M70 70 L100 65" stroke="rgba(139,92,246,0.6)" strokeWidth="0.5"/>
            <circle cx="55" cy="35" r="2" fill="#8b5cf6" />
            <circle cx="85" cy="45" r="1.5" fill="#6366f1" />
            <circle cx="70" cy="70" r="2.5" fill="#8b5cf6" className="animate-pulse"/>
            
            <defs>
               <linearGradient id="brainGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#8b5cf6" />
                  <stop offset="100%" stopColor="#3b82f6" />
               </linearGradient>
            </defs>
         </g>
         
         {/* Floating particles */}
         <g opacity="0.6">
            <circle cx="15vw" cy="25vh" r="3" fill="#8b5cf6" className="animate-pulse" filter="blur(1px)"/>
            <circle cx="80vw" cy="15vh" r="4" fill="#3b82f6" filter="blur(2px)"/>
            <circle cx="85vw" cy="75vh" r="5" fill="#a855f7" className="animate-pulse" filter="blur(2px)"/>
            <circle cx="35vw" cy="85vh" r="3" fill="#6366f1" />
            <circle cx="65vw" cy="45vh" r="2" fill="#ec4899" opacity="0.5" className="animate-pulse"/>
         </g>
       </svg>
    </div>
  );
}
