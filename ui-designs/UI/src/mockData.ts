import { User, ConsultationStep, Metric, QuestionnaireStep, Question, MultimodalStatus } from './types';

export const mockUser: User = {
  id: '20240521',
  name: '张小雨',
  avatar: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150&h=150&fit=crop',
  idNumber: '20240521',
};

export const consultationSteps: ConsultationStep[] = [
  { id: 1, label: '主诉采集', status: 'completed' },
  { id: 2, label: '现病史', status: 'active' },
  { id: 3, label: '睡眠饮食', status: 'pending' },
  { id: 4, label: '情绪体验', status: 'pending' },
  { id: 5, label: '高风险筛查', status: 'pending' },
  { id: 6, label: '总结建议', status: 'pending' },
];

export const assessmentSteps: QuestionnaireStep[] = [
  { id: 'PHQ-9', title: 'PHQ-9 抑郁筛查', status: 'active' },
  { id: 'SDS', title: 'SDS 抑郁自评', status: 'pending' },
  { id: 'SAS', title: 'SAS 焦虑自评', status: 'pending' },
  { id: 'SDSS', title: 'SDSS 社会功能', status: 'pending' },
];

export const phq9Questions: Question[] = [
  {
    id: 1,
    text: '做事时提不起劲或没有兴趣',
    options: [
      { label: '完全没有', value: 0, colorClass: 'bg-blue-50 border-blue-100' },
      { label: '几天', value: 1, colorClass: 'bg-emerald-50 border-emerald-100' },
      { label: '一半以上天数', value: 2, colorClass: 'bg-orange-50 border-orange-100' },
      { label: '几乎每天', value: 3, colorClass: 'bg-rose-50 border-rose-100' },
    ],
  },
  {
    id: 2,
    text: '感到心情低落、沮丧或绝望',
    options: [
      { label: '完全没有', value: 0, colorClass: 'bg-blue-50 border-blue-100' },
      { label: '几天', value: 1, colorClass: 'bg-emerald-50 border-emerald-100' },
      { label: '一半以上天数', value: 2, colorClass: 'bg-orange-50 border-orange-100' },
      { label: '几乎每天', value: 3, colorClass: 'bg-rose-50 border-rose-100' },
    ],
  },
  {
    id: 3,
    text: '入睡困难、多梦或早醒',
    options: [
      { label: '完全没有', value: 0, colorClass: 'bg-blue-50 border-blue-100' },
      { label: '几天', value: 1, colorClass: 'bg-emerald-50 border-emerald-100' },
      { label: '一半以上天数', value: 2, colorClass: 'bg-orange-50 border-orange-100' },
      { label: '几乎每天', value: 3, colorClass: 'bg-rose-50 border-rose-100' },
    ],
  },
];

export const emotionMetrics: Metric[] = [
  { id: 'tendency', label: '情绪倾向', value: 78, statusText: '平和', color: '#19C37D' },
  { id: 'anxiety', label: '焦虑水平', value: 62, statusText: '轻度', color: '#FFB547' },
  { id: 'stress', label: '压力指数', value: 65, statusText: '中等', color: '#0F6BFF' },
  { id: 'fatigue', label: '疲劳程度', value: 40, statusText: '较低', color: '#8b5cf6' },
];

export const multimodalStatuses: MultimodalStatus[] = [
  { id: 'face', label: '表情', status: 'good', value: 95 },
  { id: 'posture', label: '姿态', status: 'good', value: 92 },
  { id: 'voice', label: '语音', status: 'good', value: 88 },
  { id: 'eeg', label: '脑电', status: 'analyzing', value: 0 },
  { id: 'text', label: '文本', status: 'normal', value: 100 },
];
