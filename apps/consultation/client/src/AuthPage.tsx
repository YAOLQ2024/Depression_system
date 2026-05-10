import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import {
  Activity,
  Eye,
  EyeOff,
  Flower2,
  Heart,
  History,
  LayoutTemplate,
  Lock,
  MoonStar,
  Sparkles,
  Shield,
  User,
  type LucideIcon,
} from "lucide-react";
import { motion } from "motion/react";

export type AuthMode = "login" | "register";

export type AuthLoginPayload = {
  account: string;
  password: string;
};

export type AuthRegisterPayload = {
  full_name: string;
  account: string;
  password: string;
};

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
  onLogin: (payload: AuthLoginPayload) => Promise<void>;
  onRegister: (payload: AuthRegisterPayload) => Promise<void>;
};

type LoginFormState = {
  account: string;
  password: string;
};

type RegisterFormState = {
  full_name: string;
  account: string;
  password: string;
};

type InputFieldProps = {
  id: string;
  label: string;
  value: string;
  type?: "text" | "password";
  placeholder: string;
  autoComplete?: string;
  leadingIcon: LucideIcon;
  trailingAction?: ReactNode;
  focused: boolean;
  error?: string;
  showError: boolean;
  onChange: (value: string) => void;
  onBlur: () => void;
  onFocus: () => void;
};

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_REGEX = /^1\d{10}$/;

const authFeatures = [
  { title: "快速测评", icon: LayoutTemplate, desc: "基于专业量表，3-5分钟快速评估" },
  { title: "趋势追踪", icon: Activity, desc: "可视化情绪曲线，见证康复历程" },
  { title: "多模态辅助", icon: History, desc: "整合语音、表情、生理多维数据" },
  { title: "私密安全", icon: Shield, desc: "医疗级加密，全方位保护用户隐私" },
];

function normalizeAccount(account: string) {
  const trimmed = account.trim();
  return trimmed.includes("@") ? trimmed.toLowerCase() : trimmed;
}

function validateAccount(account: string) {
  const normalized = account.trim();

  if (!normalized) {
    return "请输入 11 位手机号或邮箱账号";
  }

  if (normalized.includes("@")) {
    return EMAIL_REGEX.test(normalized) ? "" : "请输入有效的邮箱地址";
  }

  return PHONE_REGEX.test(normalized) ? "" : "请输入 11 位手机号";
}

function validatePassword(password: string) {
  if (!password) {
    return "请输入密码";
  }

  return password.length >= 6 ? "" : "密码至少需要 6 位";
}

function validateFullName(fullName: string) {
  const normalized = fullName.trim();

  if (!normalized) {
    return "请输入姓名";
  }

  return normalized.length <= 40 ? "" : "姓名长度请控制在 40 个字符内";
}

function hasValidationErrors(errors: Record<string, string>) {
  return Object.values(errors).some(Boolean);
}

function AuthInputField({
  id,
  label,
  value,
  type = "text",
  placeholder,
  autoComplete,
  leadingIcon: LeadingIcon,
  trailingAction,
  focused,
  error,
  showError,
  onChange,
  onBlur,
  onFocus,
}: InputFieldProps) {
  return (
    <div className="space-y-2">
      <label className="ml-1 text-sm font-bold text-[#172033]" htmlFor={id}>
        {label}
      </label>
      <div className="relative">
        <LeadingIcon size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#6B7893]" />
        <input
          id={id}
          value={value}
          type={type}
          autoComplete={autoComplete}
          placeholder={placeholder}
          aria-invalid={showError}
          aria-describedby={showError ? `${id}-error` : undefined}
          onBlur={onBlur}
          onFocus={onFocus}
          onChange={(event) => onChange(event.target.value)}
          style={{
            paddingLeft: "3.4rem",
          }}
          className={`auth-input h-12 w-full rounded-2xl bg-white/85 pr-12 text-[#172033] outline-none transition-all placeholder:text-[#6B7893]/50 sm:h-14 ${
            showError
              ? "border border-red-300 ring-4 ring-red-100"
              : "border border-[#E6EEFB] focus:border-[#0F6BFF] focus:ring-4 focus:ring-blue-100"
          }`}
        />
        {trailingAction}
      </div>
      {showError ? (
        <p id={`${id}-error`} className="ml-1 text-xs font-medium text-[#D92D20]" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function AuthPage({
  authMode,
  passwordVisible,
  keepLoggedIn,
  loading,
  error,
  onSwitchMode,
  onTogglePassword,
  onKeepLoggedInChange,
  onLogin,
  onRegister,
}: AuthPageProps) {
  const [focusedField, setFocusedField] = useState<string | null>(null);
  const [loginForm, setLoginForm] = useState<LoginFormState>({
    account: "participant@mcs.local",
    password: "Participant123!",
  });
  const [registerForm, setRegisterForm] = useState<RegisterFormState>({
    full_name: "",
    account: "",
    password: "",
  });
  const [loginTouched, setLoginTouched] = useState<Partial<Record<keyof LoginFormState, boolean>>>({});
  const [registerTouched, setRegisterTouched] = useState<Partial<Record<keyof RegisterFormState, boolean>>>({});
  const [loginSubmitAttempted, setLoginSubmitAttempted] = useState(false);
  const [registerSubmitAttempted, setRegisterSubmitAttempted] = useState(false);

  useEffect(() => {
    setFocusedField(null);
  }, [authMode]);

  const loginErrors = {
    account: validateAccount(loginForm.account),
    password: validatePassword(loginForm.password),
  };

  const registerErrors = {
    full_name: validateFullName(registerForm.full_name),
    account: validateAccount(registerForm.account),
    password: validatePassword(registerForm.password),
  };

  async function handleLoginSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginSubmitAttempted(true);
    setLoginTouched({ account: true, password: true });

    if (hasValidationErrors(loginErrors)) {
      return;
    }

    await onLogin({
      account: normalizeAccount(loginForm.account),
      password: loginForm.password,
    });
  }

  async function handleRegisterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRegisterSubmitAttempted(true);
    setRegisterTouched({ account: true, password: true, full_name: true });

    if (hasValidationErrors(registerErrors)) {
      return;
    }

    await onRegister({
      full_name: registerForm.full_name.trim(),
      account: normalizeAccount(registerForm.account),
      password: registerForm.password,
    });
  }

  return (
    <div
      className="auth-viewport relative min-h-[100dvh] overflow-x-hidden px-4 py-4 sm:px-6 sm:py-6 lg:px-10"
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
        <div className="auth-soft-rings auth-soft-rings--left hidden xl:block" />
        <div className="auth-soft-rings auth-soft-rings--right hidden xl:block" />
        <div className="auth-soft-weave auth-soft-weave--left hidden xl:block" />
        <div className="auth-soft-weave auth-soft-weave--right hidden xl:block" />
        <motion.div
          className="auth-soft-badge auth-soft-badge--one hidden xl:flex"
          animate={{ y: [0, -8, 0], rotate: [0, -4, 0] }}
          transition={{ duration: 7.6, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
        >
          <Sparkles size={20} />
        </motion.div>
        <motion.div
          className="auth-soft-badge auth-soft-badge--two hidden xl:flex"
          animate={{ y: [0, 10, 0], rotate: [0, 5, 0] }}
          transition={{ duration: 8.4, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
        >
          <Flower2 size={20} />
        </motion.div>
        <motion.div
          className="auth-soft-badge auth-soft-badge--three hidden xl:flex"
          animate={{ y: [0, -6, 0], rotate: [0, 3, 0] }}
          transition={{ duration: 7, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
        >
          <MoonStar size={18} />
        </motion.div>
      </div>

      <div className="auth-layout relative z-10 mx-auto grid min-h-[calc(100dvh-2rem)] max-w-[1200px] grid-cols-1 items-stretch gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(360px,430px)] xl:gap-8 2xl:grid-cols-[minmax(0,1.08fr)_minmax(400px,480px)]">
        <div className="auth-marketing hidden min-h-full flex-col xl:flex">
          <div className="auth-brand-lockup mb-4 inline-flex items-center gap-4">
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

          <div className="auth-marketing-main">
            <div className="auth-hero-block mb-4">
              <span className="mb-5 inline-flex rounded-full border border-white/70 bg-[#EAF3FF] px-4 py-2 text-xs font-bold uppercase tracking-[0.14em] text-[#0F6BFF] shadow-[0_10px_25px_rgba(15,107,255,0.16)]">
                Professional Assessment
              </span>
              <h1 className="auth-hero-title text-[2.9rem] font-extrabold leading-[1.05] tracking-[-0.04em] text-[#172033] 2xl:text-[4rem]">
                探索内心，
                <br />
                <span className="text-[#4E5FF7]">重获平静的力量。</span>
              </h1>
              <p className="auth-hero-copy mt-5 max-w-[620px] text-base leading-7 text-[#6B7893] 2xl:text-lg 2xl:leading-8">
                融合专业量表与多模态数据，3-5 分钟生成可解释的心理健康建议，全流程隐私加密。
              </p>
            </div>

            <div className="auth-feature-grid grid grid-cols-1 gap-4 xl:grid-cols-2">
              {authFeatures.map((feature, index) => (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 18 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.08, duration: 0.42 }}
                  className="auth-feature-card rounded-[28px] border border-white/80 bg-white/55 p-5 shadow-[0_22px_50px_rgba(15,23,42,0.05)] backdrop-blur-md transition-all duration-200 hover:bg-white/80 hover:shadow-[0_22px_54px_rgba(15,23,42,0.08)]"
                >
                  <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl border border-blue-50 bg-white text-[#0F6BFF] shadow-[0_8px_24px_rgba(15,107,255,0.10)]">
                    <feature.icon size={20} />
                  </div>
                  <h3 className="mb-1 text-lg font-bold text-[#172033]">{feature.title}</h3>
                  <p className="text-sm leading-6 text-[#6B7893]">{feature.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="auth-badge-row mt-4 flex flex-wrap gap-4">
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

        <div className="flex items-center justify-center xl:justify-end">
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.55 }}
            className="auth-card-panel relative w-full max-w-[480px] rounded-[36px] border border-white/90 bg-white/76 p-6 shadow-[0_30px_80px_rgba(15,23,42,0.08)] backdrop-blur-2xl sm:p-8"
          >
            <div className="auth-card-soft-accent auth-card-soft-accent--top" />
            <div className="auth-card-soft-accent auth-card-soft-accent--bottom" />
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.035]"
              style={{
                backgroundImage: "radial-gradient(#0f172a 1px, transparent 0)",
                backgroundSize: "24px 24px",
              }}
            />

            <div className="relative z-10">
              <div className="mb-6 flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#0F6BFF] text-white shadow-[0_16px_30px_rgba(15,107,255,0.22)]">
                  <Heart size={20} fill="currentColor" />
                </div>
                <div>
                  <div className="text-lg font-bold text-[#172033]">SDS System</div>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[#6B7893]">
                    Mental Health Care
                  </div>
                </div>
              </div>

              <div className="mb-6">
                <h2 className="auth-card-title mb-2 text-[2rem] font-bold tracking-[-0.04em] text-[#172033] sm:text-[2.5rem]">
                  {authMode === "login" ? "欢迎回来" : "开启您的心理之旅"}
                </h2>
                <p className="text-sm leading-6 text-[#6B7893]">
                  {authMode === "login" ? "请输入您的账号与密码以继续。" : "建立健康档案后即可开始专业测评。"}
                </p>
              </div>

              <div className="mb-6 flex rounded-2xl bg-slate-100/60 p-1">
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

              {error ? (
                <div aria-live="polite" className="mb-4">
                  <div className="feedback-banner error" role="alert">
                    {error}
                  </div>
                </div>
              ) : null}

              {authMode === "login" ? (
                <form className="auth-form-stack space-y-4" onSubmit={handleLoginSubmit} noValidate>
                  <AuthInputField
                    id="login-account"
                    label="账号"
                    value={loginForm.account}
                    placeholder="请输入 11 位手机号或邮箱"
                    autoComplete="username"
                    leadingIcon={User}
                    focused={focusedField === "login-account"}
                    error={loginErrors.account}
                    showError={Boolean(loginErrors.account) && (loginTouched.account || loginSubmitAttempted)}
                    onFocus={() => setFocusedField("login-account")}
                    onBlur={() => {
                      setFocusedField((current) => (current === "login-account" ? null : current));
                      setLoginTouched((current) => ({ ...current, account: true }));
                    }}
                    onChange={(value) => setLoginForm((current) => ({ ...current, account: value }))}
                  />

                  <AuthInputField
                    id="login-password"
                    label="密码"
                    value={loginForm.password}
                    type={passwordVisible ? "text" : "password"}
                    placeholder="请输入密码"
                    autoComplete="current-password"
                    leadingIcon={Lock}
                    focused={focusedField === "login-password"}
                    error={loginErrors.password}
                    showError={Boolean(loginErrors.password) && (loginTouched.password || loginSubmitAttempted)}
                    onFocus={() => setFocusedField("login-password")}
                    onBlur={() => {
                      setFocusedField((current) => (current === "login-password" ? null : current));
                      setLoginTouched((current) => ({ ...current, password: true }));
                    }}
                    onChange={(value) => setLoginForm((current) => ({ ...current, password: value }))}
                    trailingAction={
                      <button
                        type="button"
                        aria-label={passwordVisible ? "隐藏密码" : "显示密码"}
                        onClick={onTogglePassword}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-[#6B7893] transition-colors hover:text-[#0F6BFF]"
                      >
                        {passwordVisible ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    }
                  />

                  <label htmlFor="remember-login" className="remember-login-row text-xs font-medium text-[#6B7893]">
                    <input
                      id="remember-login"
                      checked={keepLoggedIn}
                      onChange={(event) => onKeepLoggedInChange(event.target.checked)}
                      type="checkbox"
                      className="h-4 w-4 shrink-0 rounded border-[#E6EEFB] text-[#0F6BFF] focus:ring-[#0F6BFF]"
                    />
                    <span className="remember-login-text leading-5">30 天内自动登录</span>
                  </label>

                  <button
                    type="submit"
                    disabled={loading}
                    className="auth-submit flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-[#0F6BFF] text-base font-bold text-white shadow-[0_14px_30px_rgba(15,107,255,0.30)] transition-all hover:scale-[0.985] hover:bg-[#0A4BB3] hover:shadow-none active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:scale-100 sm:h-14"
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
                <form className="auth-form-stack space-y-4" onSubmit={handleRegisterSubmit} noValidate>
                  <AuthInputField
                    id="register-name"
                    label="姓名"
                    value={registerForm.full_name}
                    placeholder="请输入您的姓名"
                    autoComplete="name"
                    leadingIcon={User}
                    focused={focusedField === "register-name"}
                    error={registerErrors.full_name}
                    showError={Boolean(registerErrors.full_name) && (registerTouched.full_name || registerSubmitAttempted)}
                    onFocus={() => setFocusedField("register-name")}
                    onBlur={() => {
                      setFocusedField((current) => (current === "register-name" ? null : current));
                      setRegisterTouched((current) => ({ ...current, full_name: true }));
                    }}
                    onChange={(value) => setRegisterForm((current) => ({ ...current, full_name: value }))}
                  />

                  <AuthInputField
                    id="register-account"
                    label="账号"
                    value={registerForm.account}
                    placeholder="请输入 11 位手机号或邮箱"
                    autoComplete="username"
                    leadingIcon={User}
                    focused={focusedField === "register-account"}
                    error={registerErrors.account}
                    showError={Boolean(registerErrors.account) && (registerTouched.account || registerSubmitAttempted)}
                    onFocus={() => setFocusedField("register-account")}
                    onBlur={() => {
                      setFocusedField((current) => (current === "register-account" ? null : current));
                      setRegisterTouched((current) => ({ ...current, account: true }));
                    }}
                    onChange={(value) => setRegisterForm((current) => ({ ...current, account: value }))}
                  />

                  <AuthInputField
                    id="register-password"
                    label="密码"
                    value={registerForm.password}
                    type={passwordVisible ? "text" : "password"}
                    placeholder="请输入至少 6 位密码"
                    autoComplete="new-password"
                    leadingIcon={Lock}
                    focused={focusedField === "register-password"}
                    error={registerErrors.password}
                    showError={Boolean(registerErrors.password) && (registerTouched.password || registerSubmitAttempted)}
                    onFocus={() => setFocusedField("register-password")}
                    onBlur={() => {
                      setFocusedField((current) => (current === "register-password" ? null : current));
                      setRegisterTouched((current) => ({ ...current, password: true }));
                    }}
                    onChange={(value) => setRegisterForm((current) => ({ ...current, password: value }))}
                    trailingAction={
                      <button
                        type="button"
                        aria-label={passwordVisible ? "隐藏密码" : "显示密码"}
                        onClick={onTogglePassword}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-[#6B7893] transition-colors hover:text-[#0F6BFF]"
                      >
                        {passwordVisible ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    }
                  />

                  <button
                    type="submit"
                    disabled={loading}
                    className="auth-submit flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-[#0F6BFF] text-base font-bold text-white shadow-[0_14px_30px_rgba(15,107,255,0.30)] transition-all hover:scale-[0.985] hover:bg-[#0A4BB3] hover:shadow-none active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:scale-100 sm:h-14"
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
