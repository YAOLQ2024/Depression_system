import { 
  ConsultationStartResponse, 
  ConsultationState, 
  MessageResponse, 
  MultimodalData 
} from '../types/consultation';

// Define a delay helper to simulate network latency
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const mockConsultationService = {
  startConsultation: async (userId: string): Promise<ConsultationStartResponse> => {
    await delay(600);
    return {
      sessionId: `sess_${Date.now()}`,
      digitalHuman: {
        idleVideoUrl: "mock_idle.mp4",
        speakingVideoUrl: "mock_speaking.mp4",
        posterUrl: "https://images.unsplash.com/photo-1594824436998-dd40e4f208c9?q=80&w=1470&auto=format&fit=crop", // Professional doctor placeholder
      },
      initialMessage: "您好，我将协助您完成心理状态评估。",
      currentStep: 1,
      cameraEnabled: true,
      multimodalEnabled: true
    };
  },

  getState: async (sessionId: string): Promise<ConsultationState> => {
    await delay(300);
    return {
      sessionId,
      currentStep: 2,
      currentQuestion: "最近让您感到困扰的主要问题是什么？",
      assistantMessage: "我们开始吧。首先，请您和我说说，最近让您感到困扰的主要问题是什么呢？",
      status: 'active'
    };
  },

  sendMessage: async (sessionId: string, transcript: string): Promise<MessageResponse> => {
    await delay(1000); // Simulate processing and AI generation
    return {
      assistantMessage: "这种情况大概持续多久了？",
      nextQuestion: "这种情况大概持续多久了？",
      currentStep: 2,
      riskFlag: false,
      digitalHumanState: "speaking"
    };
  },

  getMultimodalData: async (sessionId: string): Promise<MultimodalData> => {
    // Generate some randomized data to make the waveforms look alive
    const generateWave = (base: number, length: number = 20) => {
      return Array.from({length}, () => base + (Math.random() * 0.4 - 0.2));
    };

    return {
      eeg: {
        alpha: 45 + Math.floor(Math.random() * 10),
        beta: 32 + Math.floor(Math.random() * 10),
        theta: 18 + Math.floor(Math.random() * 5),
        delta: 5 + Math.floor(Math.random() * 2),
        waveform: generateWave(0.5, 40) // Data for charting, scaled between 0 and 1
      },
      emotion: {
        label: "中等偏低",
        score: 60 + Math.floor(Math.random() * 5),
        confidence: 0.86
      },
      anxiety: {
        label: "中等",
        score: 55 + Math.floor(Math.random() * 10)
      },
      stress: {
        label: "偏高",
        score: 62 + Math.floor(Math.random() * 8)
      },
      cognitiveLoad: {
        label: "正常",
        score: 40 + Math.floor(Math.random() * 5)
      },
      fatigue: {
        label: "偏高",
        score: 68 + Math.floor(Math.random() * 6)
      },
      connections: {
        eeg: true,
        face: true,
        voice: true,
        physiology: false
      }
    };
  },

  endConsultation: async (sessionId: string): Promise<{success: boolean}> => {
    await delay(500);
    return { success: true };
  }
};
