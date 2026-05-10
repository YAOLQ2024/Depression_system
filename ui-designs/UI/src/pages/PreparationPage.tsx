import React, { useState } from 'react';
import { ShieldCheck, Video, Mic, Wifi, ChevronRight, UserPlus, FileClock, History } from 'lucide-react';
import { motion } from 'motion/react';

interface PreparationPageProps {
  onStart: () => void;
}

const PreparationPage: React.FC<PreparationPageProps> = ({ onStart }) => {
  const [formData, setFormData] = useState({
    name: '张小雨',
    age: '24',
    height: '165',
    weight: '52',
    maritalStatus: '未婚',
    parentMaritalStatus: '良好',
    parentOccupation: '教师 / 公务员',
    psychHistory: '无',
    familyHistory: '无',
  });

  const deviceStatus = [
    { label: '麦克风', icon: Mic, status: 'connected', color: 'text-emerald-500' },
    { label: '摄像头', icon: Video, status: 'connected', color: 'text-emerald-500' },
    { label: '网络状态', icon: Wifi, status: 'excellent', color: 'text-[#0F6BFF]' },
    { label: '语音权限', icon: ShieldCheck, status: 'granted', color: 'text-emerald-500' },
  ];

  return (
    <div className="max-w-[1000px] mx-auto space-y-8">
      <div className="flex flex-col md:flex-row gap-8">
        {/* Left Side: Form */}
        <div className="flex-1">
          <div className="bg-white rounded-[32px] p-8 shadow-sm border border-[#E6EEFB]">
            <div className="flex items-center gap-3 mb-8">
               <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center text-[#0F6BFF]">
                 <UserPlus size={20} />
               </div>
               <h2 className="text-xl font-bold text-[#172033]">基础信息收集</h2>
            </div>

            <div className="grid grid-cols-2 gap-6">
              {[
                { label: '姓名', key: 'name' },
                { label: '年龄', key: 'age' },
                { label: '身高 (cm)', key: 'height' },
                { label: '体重 (kg)', key: 'weight' },
                { label: '婚姻状况', key: 'maritalStatus' },
                { label: '父母婚姻状况', key: 'parentMaritalStatus' },
                { label: '父母职业', key: 'parentOccupation' },
                { label: '既往就诊史', key: 'psychHistory' },
                { label: '家族史', key: 'familyHistory' },
              ].map((field) => (
                <div key={field.key} className="space-y-2">
                  <label className="text-sm font-bold text-[#6B7893] ml-1">{field.label}</label>
                  <input
                    type="text"
                    value={formData[field.key as keyof typeof formData]}
                    onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                    className="w-full h-12 px-4 bg-[#F5F8FF]/50 border border-[#E6EEFB] rounded-xl focus:ring-4 focus:ring-blue-100 focus:border-[#0F6BFF] outline-none transition-all"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Side: Sidebar Info */}
        <div className="w-full md:w-[320px] space-y-6">
          <div className="bg-white rounded-3xl p-6 shadow-sm border border-[#E6EEFB]">
            <h3 className="font-bold text-[#172033] mb-4 flex items-center gap-2">
               <div className="w-1.5 h-4 bg-[#0F6BFF] rounded-full" />
               问诊说明
            </h3>
            <ul className="space-y-4">
              <li className="flex gap-3">
                <div className="mt-1 w-5 h-5 rounded-full bg-blue-50 flex items-center justify-center shrink-0">
                  <span className="text-[10px] font-bold text-[#0F6BFF]">1</span>
                </div>
                <p className="text-xs text-[#6B7893] leading-relaxed">请在安静、光线充足的环境下进行，确保摄像头可以清晰捕捉面部表情。</p>
              </li>
              <li className="flex gap-3">
                <div className="mt-1 w-5 h-5 rounded-full bg-blue-50 flex items-center justify-center shrink-0">
                  <span className="text-[10px] font-bold text-[#0F6BFF]">2</span>
                </div>
                <p className="text-xs text-[#6B7893] leading-relaxed">问诊过程受多模态情绪感知系统实时监测，请如实反馈您的真实感受。</p>
              </li>
              <li className="flex gap-3">
                <div className="mt-1 w-5 h-5 rounded-full bg-blue-50 flex items-center justify-center shrink-0">
                  <span className="text-[10px] font-bold text-[#0F6BFF]">3</span>
                </div>
                <p className="text-xs text-[#6B7893] leading-relaxed">所有数据均通过 AES-256 加密存储，仅用于本次心理健康评估分析。</p>
              </li>
            </ul>
          </div>

          <div className="bg-white rounded-3xl p-6 shadow-sm border border-[#E6EEFB]">
            <h3 className="font-bold text-[#172033] mb-4 flex items-center gap-2">
               <div className="w-1.5 h-4 bg-emerald-500 rounded-full" />
               设备状态检测
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {deviceStatus.map((device) => (
                <div key={device.label} className="p-3 bg-[#F5F8FF]/50 border border-[#E6EEFB] rounded-2xl flex flex-col items-center gap-2">
                   <device.icon className={device.color} size={20} />
                   <span className="text-[10px] font-bold text-[#172033]">{device.label}</span>
                   <span className="text-[9px] text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">正常</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-3xl p-6 border border-blue-100 flex items-start gap-4">
             <div className="w-10 h-10 bg-white rounded-xl shadow-sm flex items-center justify-center">
                <History size={20} className="text-blue-600" />
             </div>
             <div>
                <h4 className="text-sm font-bold text-blue-900 mb-1">历史纪录</h4>
                <p className="text-[10px] text-blue-700/70 leading-relaxed">系统检测到您最近一次在 2026-04-10 完成过评估。</p>
             </div>
          </div>
        </div>
      </div>

      {/* Bottom Actions */}
      <div className="flex items-center justify-between bg-white/50 backdrop-blur-md p-6 rounded-[32px] border border-white">
        <div className="flex items-center gap-4">
          <div className="flex -space-x-2">
            {[1,2,3].map(i => (
              <div key={i} className="w-8 h-8 rounded-full border-2 border-white bg-blue-100 overflow-hidden">
                <img src={`https://i.pravatar.cc/150?u=${i}`} alt="Avatar" className="w-full h-full object-cover" />
              </div>
            ))}
          </div>
          <p className="text-xs text-[#6B7893] font-medium">已有来自 3,240+ 位用户的专业数据模型支持</p>
        </div>

        <div className="flex gap-4">
          <button className="h-14 px-8 border border-[#E6EEFB] bg-white text-[#6B7893] font-bold rounded-2xl hover:bg-gray-50 transition-all">
            保存资料
          </button>
          <button 
            onClick={onStart}
            className="h-14 px-10 bg-[#0F6BFF] text-white font-bold rounded-2xl shadow-lg shadow-blue-500/20 hover:shadow-none hover:translate-y-0.5 transition-all flex items-center gap-2"
          >
            开始问诊
            <ChevronRight size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default PreparationPage;
