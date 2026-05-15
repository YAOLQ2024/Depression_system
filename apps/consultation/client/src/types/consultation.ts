export interface DigitalHuman {
  idleVideoUrl: string;
  speakingVideoUrl: string;
  posterUrl: string;
}

export interface ConsultationStartResponse {
  sessionId: string;
  digitalHuman: DigitalHuman;
  initialMessage: string;
  currentStep: number;
  cameraEnabled: boolean;
  multimodalEnabled: boolean;
}

export interface ConsultationState {
  sessionId: string;
  currentStep: number;
  currentQuestion: string;
  assistantMessage: string;
  status: 'active' | 'ended';
}

export interface MessageResponse {
  assistantMessage: string;
  nextQuestion: string;
  currentStep: number;
  riskFlag: boolean;
  digitalHumanState: 'idle' | 'speaking';
}

export interface MultimodalData {
  eeg: {
    alpha: number;
    beta: number;
    theta: number;
    delta: number;
    waveform: number[];
  };
  emotion: {
    label: string;
    score: number;
    confidence: number;
  };
  anxiety: {
    label: string;
    score: number;
  };
  stress: {
    label: string;
    score: number;
  };
  cognitiveLoad: {
    label: string;
    score: number;
  };
  fatigue: {
    label: string;
    score: number;
  };
  connections: {
    eeg: boolean;
    face: boolean;
    voice: boolean;
    physiology: boolean;
  };
}
