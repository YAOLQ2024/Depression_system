export type PageState = 'auth' | 'preparation' | 'consultation' | 'assessment' | 'result';

export interface User {
  id: string;
  name: string;
  avatar?: string;
  idNumber: string;
}

export interface ConsultationStep {
  id: number;
  label: string;
  status: 'pending' | 'active' | 'completed';
}

export interface Metric {
  id: string;
  label: string;
  value: number;
  statusText: string;
  color: string;
}

export interface QuestionnaireStep {
  id: string;
  title: string;
  status: 'pending' | 'active' | 'completed';
}

export interface Question {
  id: number;
  text: string;
  options: {
    label: string;
    value: number;
    colorClass: string;
  }[];
}

export interface MultimodalStatus {
  id: string;
  label: string;
  status: 'normal' | 'analyzing' | 'good' | 'risk';
  value: number; // percentage or level
}
