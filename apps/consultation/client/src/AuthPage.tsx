import type { FormEvent } from "react";

import { Activity, Eye, EyeOff, Heart, History, LayoutTemplate, Lock, Shield, User } from "lucide-react";
import { motion } from "motion/react";

type AuthMode = "login" | "register";

type AuthPageProps = {
  authMode: AuthMode;
  passwordVisible: boolean;
  keepLoggedIn: boolean;
  loading: boolean;
  message: string;
  error: string;
  onSwitchMode: (mode: AuthMode) => void;
  onTogglePassword: () => void;
  onKeepLoggedInChange: (checked: boolean) => void;
  onLogin: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onRegister: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

const authFeatures = [
  { title: "快速测评", icon: LayoutTemplate, desc: "基于专业量表，3-5分钟快速评估" },
  { title: "趋势追踪", icon: Activity, desc: "可视化情绪曲线，见证康复历程" },
  { title: "多模态辅助", icon: History, desc: "整合语音、表情、生理多维数据" },
  { title: "私密安全", icon: Shield, desc: "医疗级加密，全方位保护用户隐私" },
];

function AuthPage({
  authMode,
  passwordVisible,
  keepLoggedIn,
  loading,
  message,
  error,
  onSwitchMode,
  onTogglePassword,
  onKeepLoggedInChange,
  onLogin,
  onRegister,
}: AuthPageProps) {
  return (
    <div
      className="relative min-h-screen overflow-hidden px-6 py-10 sm:px-8 lg:px-12"
      style={{
        background:
          "radial-gradient(circle at 0% 15%, rgba(84, 208, 255, 0.28), transparent 22%), radial-gradient(circle at 100% 10%, rgba(255, 212, 129, 0.24), transparent 24%), radial-gradient(circle at 50% 100%, rgba(69, 119, 255, 0.18), transparent 28%), linear-gradient(180deg, #eef5ff 0%, #f9fbff 100%)",
      }}
    >
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-[-4rem] top-[16%] h-40 w-40 rounded-full bg-[#ffe6a3]/60 blur-3xl" />
        <div className="absolute left-[8%] top-[40%] h-28 w-28 rounded-full bg-[#d6f0ff]/80 blur-2xl" />
        <div className="absolute bottom-[-3rem] left-[42%] h-36 w-36 rounded-full bg-[#aaccff]/60 blur-3xl" />
        <div className="absolute right-[4%] top-[22%] h-40 w-40 rounded-full bg-[#ffe9c4]/60 blur-3xl" />
        <div className="absolute right-[-3rem] bottom-[6%] h-44 w-44 rounded-full bg-[#d7e7ff]/80 blur-3xl" />
      </div>

      <div className="relative z-10 mx-auto grid min-h-[calc(100vh-5rem)] max-w-[1200px] grid-cols-1 items-center gap-12 lg:grid-cols-[minmax(0,1.08fr)_minmax(420px,480px)]">
        <div className="flex flex-col justify-center">
          <div className="mb-10 inline-flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#0F6BFF] text-white shadow-[0_22px_40px_rgba(15,107,255,0.30)]">
              <Heart size={26} fill="currentColor" />
            </div>
            <div>
              <div className="text-[2rem] font-bold leading-none text-[#172033]">SDS System</div>
              <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.32em] text-[#6B7893]">
                Mental Health Care
              </div>
            </div>
          </div>

          <div className="mb-8">
            <span className="mb-5 inline-flex rounded-full border border-white/70 bg-[#EAF3FF] px-4 py-2 text-xs font-bold uppercase tracking-[0.14em] text-[#0F6BFF] shadow-[0_10px_25px_rgba(15,107,255,0.16)]">
              Professional Assessment
            </span>
            <h1 className="text-[3rem] font-extrabold leading-[1.05] tracking-[-0.04em] text-[#172033] sm:text-[4.25rem]">
              探索内心，
              <br />
              <span className="text-[#4E5FF7]">重获平静的力量。</span>
            </h1>
            <p className="mt-5 max-w-[620px] text-lg leading-8 text-[#6B7893]">
              融合专业量表与多模态数据，3-5 分钟生成可解释的心理健康建议，全流程隐私加密。
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {authFeatures.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.08, duration: 0.42 }}
                className="rounded-[28px] border border-white/80 bg-white/55 p-5 shadow-[0_22px_50px_rgba(15,23,42,0.05)] backdrop-blur-md transition-all duration-200 hover:bg-white/80 hover:shadow-[0_22px_54px_rgba(15,23,42,0.08)]"
              >
                <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl border border-blue-50 bg-white text-[#0F6BFF] shadow-[0_8px_24px_rgba(15,107,255,0.10)]">
                  <feature.icon size={20} />
                </div>
                <h3 className="mb-1 text-lg font-bold text-[#172033]">{feature.title}</h3>
                <p className="text-sm leading-6 text-[#6B7893]">{feature.desc}</p>
              </motion.div>
            ))}
          </div>

          <div className="mt-10 flex flex-wrap gap-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/70 bg-white/45 px-4 py-2 text-xs font-medium text-[#6B7893] backdrop-blur-md">
              <Shield size={14} className="text-emerald-500" />
              数据隐私保护
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/70 bg-white/45 px-4 py-2 text-xs font-medium text-[#6B7893] backdrop-blur-md">
              <Lock size={14} className="text-[#0F6BFF]" />
              仅供参考，非医疗诊断
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center lg:justify-end">
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.55 }}
            className="relative w-full max-w-[480px] rounded-[40px] border border-white/90 bg-white/72 p-8 shadow-[0_30px_80px_rgba(15,23,42,0.08)] backdrop-blur-2xl sm:p-10"
          >
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.035]"
              style={{
                backgroundImage: "radial-gradient(#0f172a 1px, transparent 0)",
                backgroundSize: "24px 24px",
              }}
            />

            <div className="relative z-10">
              <div className="mb-10">
                <h2 className="mb-2 text-4xl font-bold tracking-[-0.04em] text-[#172033]">
                  {authMode === "login" ? "欢迎回来" : "开启您的心理之旅"}
                </h2>
                <p className="text-sm leading-6 text-[#6B7893]">
                  {authMode === "login" ? "请输入您的账号以继续。" : "建立您的健康档案，开始专业测评。"}
                </p>
              </div>

              <div className="mb-8 flex rounded-2xl bg-slate-100/60 p-1">
                <button
                  type="button"
                  onClick={() => onSwitchMode("login")}
                  className={`flex-1 rounded-xl py-3 text-sm font-bold transition-all ${
                    authMode === "login" ? "bg-white text-[#0F6BFF] shadow-sm" : "text-[#6B7893]"
                  }`}
                >
                  登录
                </button>
                <button
                  type="button"
                  onClick={() => onSwitchMode("register")}
                  className={`flex-1 rounded-xl py-3 text-sm font-bold transition-all ${
                    authMode === "register" ? "bg-white text-[#0F6BFF] shadow-sm" : "text-[#6B7893]"
                  }`}
                >
                  注册
                </button>
              </div>

              <div aria-live="polite" className="mb-6 space-y-3">
                {message ? <div className="feedback-banner success">{message}</div> : null}
                {error ? (
                  <div className="feedback-banner error" role="alert">
                    {error}
                  </div>
                ) : null}
              </div>

              {authMode === "login" ? (
                <form className="space-y-6" onSubmit={onLogin}>
                  <div className="space-y-2">
                    <label className="ml-1 text-sm font-bold text-[#172033]" htmlFor="login-email">
                      账号
                    </label>
                    <div className="relative">
                      <User size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#6B7893]" />
                      <input
                        id="login-email"
                        name="email"
                        type="email"
                        required
                        defaultValue="participant@mcs.local"
                        placeholder="用户名 / 手机号 / 邮箱"
                        className="h-14 w-full rounded-2xl border border-[#E6EEFB] bg-white/80 pl-12 pr-4 text-[#172033] outline-none transition-all placeholder:text-[#6B7893]/50 focus:border-[#0F6BFF] focus:ring-4 focus:ring-blue-100"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between px-1">
                      <label className="text-sm font-bold text-[#172033]" htmlFor="login-password">
                        密码
                      </label>
                      <button type="button" className="text-[10px] font-bold text-[#0F6BFF] hover:underline">
                        忘记密码?
                      </button>
                    </div>
                    <div className="relative">
                      <Lock size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#6B7893]" />
                      <input
                        id="login-password"
                        name="password"
                        type={passwordVisible ? "text" : "password"}
                        required
                        defaultValue="Participant123!"
                        placeholder="请输入密码"
                        className="h-14 w-full rounded-2xl border border-[#E6EEFB] bg-white/80 pl-12 pr-12 text-[#172033] outline-none transition-all placeholder:text-[#6B7893]/50 focus:border-[#0F6BFF] focus:ring-4 focus:ring-blue-100"
                      />
                      <button
                        type="button"
                        aria-label={passwordVisible ? "隐藏密码" : "显示密码"}
                        onClick={onTogglePassword}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-[#6B7893] transition-colors hover:text-[#0F6BFF]"
                      >
                        {passwordVisible ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 px-1">
                    <input
                      id="remember-login"
                      checked={keepLoggedIn}
                      onChange={(event) => onKeepLoggedInChange(event.target.checked)}
                      type="checkbox"
                      className="h-4 w-4 rounded border-[#E6EEFB] text-[#0F6BFF] focus:ring-[#0F6BFF]"
                    />
                    <label htmlFor="remember-login" className="text-xs font-medium text-[#6B7893]">
                      30天内自动登录
                    </label>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-[#0F6BFF] text-base font-bold text-white shadow-[0_14px_30px_rgba(15,107,255,0.30)] transition-all hover:scale-[0.985] hover:bg-[#0A4BB3] hover:shadow-none active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:scale-100"
                  >
                    {loading ? "登录中..." : "登 录"}
                  </button>

                  <div className="pt-1 text-center">
                    <p className="text-xs text-[#6B7893]">
                      还没有账号？
                      <button
                        type="button"
                        onClick={() => onSwitchMode("register")}
                        className="ml-1 font-bold text-[#0F6BFF] hover:underline"
                      >
                        立即注册
                      </button>
                    </p>
                  </div>
                </form>
              ) : (
                <form className="space-y-6" onSubmit={onRegister}>
                  <div className="space-y-2">
                    <label className="ml-1 text-sm font-bold text-[#172033]" htmlFor="register-name">
                      姓名
                    </label>
                    <div className="relative">
                      <User size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#6B7893]" />
                      <input
                        id="register-name"
                        name="full_name"
                        type="text"
                        required
                        placeholder="您的真实姓名"
                        className="h-14 w-full rounded-2xl border border-[#E6EEFB] bg-white/80 pl-12 pr-4 text-[#172033] outline-none transition-all placeholder:text-[#6B7893]/50 focus:border-[#0F6BFF] focus:ring-4 focus:ring-blue-100"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="ml-1 text-sm font-bold text-[#172033]" htmlFor="register-email">
                      账号
                    </label>
                    <div className="relative">
                      <User size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#6B7893]" />
                      <input
                        id="register-email"
                        name="email"
                        type="email"
                        required
                        placeholder="用户名 / 手机号 / 邮箱"
                        className="h-14 w-full rounded-2xl border border-[#E6EEFB] bg-white/80 pl-12 pr-4 text-[#172033] outline-none transition-all placeholder:text-[#6B7893]/50 focus:border-[#0F6BFF] focus:ring-4 focus:ring-blue-100"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="ml-1 text-sm font-bold text-[#172033]" htmlFor="register-password">
                      密码
                    </label>
                    <div className="relative">
                      <Lock size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#6B7893]" />
                      <input
                        id="register-password"
                        name="password"
                        type={passwordVisible ? "text" : "password"}
                        required
                        placeholder="请输入密码"
                        className="h-14 w-full rounded-2xl border border-[#E6EEFB] bg-white/80 pl-12 pr-12 text-[#172033] outline-none transition-all placeholder:text-[#6B7893]/50 focus:border-[#0F6BFF] focus:ring-4 focus:ring-blue-100"
                      />
                      <button
                        type="button"
                        aria-label={passwordVisible ? "隐藏密码" : "显示密码"}
                        onClick={onTogglePassword}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-[#6B7893] transition-colors hover:text-[#0F6BFF]"
                      >
                        {passwordVisible ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-[#0F6BFF] text-base font-bold text-white shadow-[0_14px_30px_rgba(15,107,255,0.30)] transition-all hover:scale-[0.985] hover:bg-[#0A4BB3] hover:shadow-none active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:scale-100"
                  >
                    {loading ? "提交中..." : "立 即 注 册"}
                  </button>

                  <div className="pt-1 text-center">
                    <p className="text-xs text-[#6B7893]">
                      已有账号？
                      <button
                        type="button"
                        onClick={() => onSwitchMode("login")}
                        className="ml-1 font-bold text-[#0F6BFF] hover:underline"
                      >
                        返回登录
                      </button>
                    </p>
                  </div>
                </form>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

export default AuthPage;
