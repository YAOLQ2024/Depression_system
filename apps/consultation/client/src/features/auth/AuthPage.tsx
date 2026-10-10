import { useState, type CSSProperties, type FormEvent, type ReactNode } from "react";

import {
  ArrowLeft,
  ChartNoAxesColumn,
  ShieldCheck,
  UserRound,
  Eye,
  EyeOff,
} from "lucide-react";
import { Link } from "react-router-dom";

import { EntryBrand, entryBackgroundStyle } from "../../components/entry-chrome";
import { APP_PATHS } from "../../routes";

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
  trailingAction?: ReactNode;
  error?: string;
  showError: boolean;
  onChange: (value: string) => void;
  onBlur: () => void;
};

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_REGEX = /^1\d{10}$/;
const AUTH_CUBE_SIZE = "clamp(8.8rem, 12vw, 12.2rem)";
const AUTH_CUBE_DEPTH = "calc(var(--cube-size) / 2)";
const AUTH_CUBE_FACE_TRANSFORMS = [
  `rotateY(0deg) translateZ(${AUTH_CUBE_DEPTH})`,
  `rotateY(180deg) translateZ(${AUTH_CUBE_DEPTH})`,
  `rotateY(90deg) translateZ(${AUTH_CUBE_DEPTH})`,
  `rotateY(-90deg) translateZ(${AUTH_CUBE_DEPTH})`,
  `rotateX(90deg) translateZ(${AUTH_CUBE_DEPTH})`,
  `rotateX(-90deg) translateZ(${AUTH_CUBE_DEPTH})`,
];

type OrbitLayer = {
  id: string;
  reverse?: boolean;
  style: CSSProperties;
  satellites: Array<{
    id: string;
    className: string;
    style?: CSSProperties;
  }>;
};

const AUTH_ORBIT_LAYERS: OrbitLayer[] = [
  {
    id: "equatorial",
    style: {
      "--orbit-size": "58%",
      "--orbit-duration": "14s",
      "--orbit-tilt-x": "72deg",
      "--orbit-tilt-y": "0deg",
      "--orbit-rotate-z": "8deg",
      "--orbit-ring-color": "rgba(216, 206, 255, 0.52)",
      "--orbit-ring-glow": "rgba(125, 105, 255, 0.24)",
    } as CSSProperties,
    satellites: [
      { id: "north", className: "auth-orbit-satellite auth-orbit-satellite-top", style: { "--satellite-size": "2rem" } as CSSProperties },
      { id: "south", className: "auth-orbit-satellite auth-orbit-satellite-bottom", style: { "--satellite-size": "1.8rem" } as CSSProperties },
    ],
  },
  {
    id: "polar",
    reverse: true,
    style: {
      "--orbit-size": "72%",
      "--orbit-duration": "19s",
      "--orbit-tilt-x": "32deg",
      "--orbit-tilt-y": "68deg",
      "--orbit-rotate-z": "22deg",
      "--orbit-ring-color": "rgba(205, 223, 255, 0.4)",
      "--orbit-ring-glow": "rgba(124, 168, 255, 0.2)",
    } as CSSProperties,
    satellites: [
      { id: "left", className: "auth-orbit-satellite auth-orbit-satellite-left", style: { "--satellite-size": "1.7rem" } as CSSProperties },
      { id: "right", className: "auth-orbit-satellite auth-orbit-satellite-right", style: { "--satellite-size": "1.82rem" } as CSSProperties },
    ],
  },
  {
    id: "oblique",
    style: {
      "--orbit-size": "86%",
      "--orbit-duration": "24s",
      "--orbit-tilt-x": "82deg",
      "--orbit-tilt-y": "44deg",
      "--orbit-rotate-z": "-18deg",
      "--orbit-ring-color": "rgba(241, 222, 255, 0.34)",
      "--orbit-ring-glow": "rgba(166, 118, 255, 0.2)",
    } as CSSProperties,
    satellites: [
      { id: "top", className: "auth-orbit-satellite auth-orbit-satellite-top", style: { "--satellite-size": "1.55rem" } as CSSProperties },
      { id: "right", className: "auth-orbit-satellite auth-orbit-satellite-right", style: { "--satellite-size": "1.42rem" } as CSSProperties },
    ],
  },
  {
    id: "outer",
    reverse: true,
    style: {
      "--orbit-size": "98%",
      "--orbit-duration": "31s",
      "--orbit-tilt-x": "38deg",
      "--orbit-tilt-y": "-62deg",
      "--orbit-rotate-z": "36deg",
      "--orbit-ring-color": "rgba(233, 237, 255, 0.3)",
      "--orbit-ring-glow": "rgba(147, 129, 255, 0.18)",
    } as CSSProperties,
    satellites: [
      { id: "left", className: "auth-orbit-satellite auth-orbit-satellite-left", style: { "--satellite-size": "1.3rem" } as CSSProperties },
      { id: "bottom", className: "auth-orbit-satellite auth-orbit-satellite-bottom", style: { "--satellite-size": "1.45rem" } as CSSProperties },
    ],
  },
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
  trailingAction,
  error,
  showError,
  onChange,
  onBlur,
}: InputFieldProps) {
  return (
    <div className="auth-field mb-5">
      <label className="mb-2.5 block text-base font-semibold tracking-[0.03em] text-[#2c3e50]" htmlFor={id}>
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          value={value}
          type={type}
          autoComplete={autoComplete}
          placeholder={placeholder}
          aria-invalid={showError}
          aria-describedby={showError ? `${id}-error` : undefined}
          onBlur={onBlur}
          onChange={(event) => onChange(event.target.value)}
          className={`h-[52px] w-full rounded-[10px] border bg-[#f8f9fc] px-4 pr-12 text-base font-normal text-[#2c3e50] outline-none transition placeholder:text-[15px] placeholder:text-[#a0a0a0] ${
            showError
              ? "border-red-300 bg-red-50/70 shadow-[0_0_0_3px_rgba(248,113,113,0.08)]"
              : "border-[#e1e5e9] hover:border-[#4f81ff] focus:border-[#4f81ff] focus:shadow-[0_0_0_3px_rgba(79,129,255,0.10)]"
          }`}
        />
        {trailingAction}
      </div>
      {showError ? (
        <p id={`${id}-error`} className="mt-1.5 text-xs font-medium text-red-600" role="alert">
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
    <main className="auth-page relative min-h-[100svh] overflow-hidden bg-[#f5f7fa]" style={entryBackgroundStyle}>
      <div className="auth-backdrop absolute inset-0 bg-[linear-gradient(135deg,rgba(10,18,40,0.44)_0%,rgba(10,18,40,0.22)_42%,rgba(10,18,40,0.12)_100%)] lg:hidden" />

      <EntryBrand className="auth-brand left-[clamp(1rem,2vw,2.2rem)] top-[clamp(1rem,2vw,2rem)]" />

      <div className="auth-layout relative z-10 flex min-h-[100svh]">
        <section className="auth-visual relative hidden flex-1 overflow-hidden lg:flex">
          <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(8,18,44,0.62)_0%,rgba(10,22,52,0.34)_40%,rgba(10,22,52,0.18)_100%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_24%_24%,rgba(255,255,255,0.22),transparent_18%),radial-gradient(circle_at_78%_26%,rgba(124,92,255,0.28),transparent_20%),radial-gradient(circle_at_56%_78%,rgba(170,148,255,0.18),transparent_22%)]" />

          <div className="relative z-10 mx-auto flex w-full max-w-[1600px] items-center justify-center px-[clamp(2rem,4vw,6rem)]">
            <div className="auth-stage relative aspect-square w-[min(72vw,860px)] min-w-[480px] max-w-[860px] animate-auth-stage-drift [perspective:1800px]">
              <div className="absolute left-1/2 top-1/2 h-[46%] w-[46%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(167,145,255,0.42)_0%,rgba(119,103,255,0.18)_44%,transparent_74%)] blur-[42px] animate-auth-core-pulse" />
              <div className="absolute left-1/2 top-1/2 h-[24%] w-[24%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.92)_0%,rgba(215,202,255,0.52)_44%,transparent_76%)] blur-[22px] opacity-85" />

              {AUTH_ORBIT_LAYERS.map((layer) => (
                <div key={layer.id} className="auth-orbit-plane" style={layer.style}>
                  <div className={layer.reverse ? "auth-orbit-track auth-orbit-track-reverse" : "auth-orbit-track"}>
                    {layer.satellites.map((satellite) => (
                      <span
                        key={satellite.id}
                        className={satellite.className}
                        style={satellite.style}
                      />
                    ))}
                  </div>
                </div>
              ))}

              <div className="auth-cube absolute left-1/2 top-1/2 h-[var(--cube-size)] w-[var(--cube-size)] -translate-x-1/2 -translate-y-1/2 [transform-style:preserve-3d]" style={{ "--cube-size": AUTH_CUBE_SIZE } as CSSProperties}>
                <div className="absolute inset-[8%] rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.16)_0%,rgba(116,99,255,0.08)_45%,transparent_72%)] blur-xl" />
                <div
                  className="auth-cube-spinner absolute inset-0 animate-auth-cube-spin"
                  style={{ transformStyle: "preserve-3d", "--cube-size": AUTH_CUBE_SIZE } as CSSProperties}
                >
                  {AUTH_CUBE_FACE_TRANSFORMS.map((transform) => (
                    <span
                      key={transform}
                      className="absolute inset-0 border border-white/24 bg-[linear-gradient(145deg,rgba(183,197,255,0.95)_0%,rgba(109,120,255,0.9)_34%,rgba(113,87,255,0.96)_68%,rgba(61,43,209,0.98)_100%)] shadow-[0_24px_54px_rgba(106,92,255,0.28)]"
                      style={{ transform }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="auth-panel relative flex w-full items-center justify-center bg-white/94 px-8 py-24 backdrop-blur-sm lg:w-[450px] lg:min-w-[450px] lg:bg-white lg:px-0 lg:py-0 lg:shadow-[-2px_0_20px_rgba(0,0,0,0.10)]">
          <div className="auth-card w-full max-w-[320px] py-4 lg:py-10">
            <div className="auth-heading mb-10 text-center">
              <div className="mb-4">
                <span className="auth-heading-badge inline-flex items-center rounded-[8px] bg-[linear-gradient(45deg,#4f81ff,#3b66db)] px-6 py-3 text-[20px] font-bold tracking-[0.12em] text-white shadow-[0_4px_12px_rgba(79,129,255,0.30)]">
                  {authMode === "login" ? "智能评估" : "创建账号"}
                </span>
              </div>
              <p className="m-0 text-base leading-7 text-[#555]">
                {authMode === "login" ? "请输入账号与密码，开始本次评估。" : "填写基础信息后即可创建受试者账号。"}
              </p>
            </div>

            {error ? (
              <div className="mb-5 rounded-[10px] border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700" role="alert">
                {error}
              </div>
            ) : null}

            {authMode === "login" ? (
              <form onSubmit={handleLoginSubmit} noValidate>
                <AuthInputField
                  id="login-account"
                  label="账号"
                  value={loginForm.account}
                  placeholder="请输入 11 位手机号或邮箱"
                  autoComplete="username"
                  error={loginErrors.account}
                  showError={Boolean(loginErrors.account) && (loginTouched.account || loginSubmitAttempted)}
                  onBlur={() => {
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
                  error={loginErrors.password}
                  showError={Boolean(loginErrors.password) && (loginTouched.password || loginSubmitAttempted)}
                  onBlur={() => {
                    setLoginTouched((current) => ({ ...current, password: true }));
                  }}
                  onChange={(value) => setLoginForm((current) => ({ ...current, password: value }))}
                  trailingAction={
                    <button
                      type="button"
                      aria-label={passwordVisible ? "隐藏密码" : "显示密码"}
                      onClick={onTogglePassword}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-[#98a2b3] transition hover:text-[#4f81ff]"
                    >
                      {passwordVisible ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  }
                />

                <div className="auth-options mb-6 flex items-center justify-between gap-4 text-[15px]">
                  <label htmlFor="remember-login" className="inline-flex items-center gap-2.5 text-[#666]">
                    <input
                      id="remember-login"
                      checked={keepLoggedIn}
                      onChange={(event) => onKeepLoggedInChange(event.target.checked)}
                      type="checkbox"
                      className="h-4 w-4 rounded border-slate-300 text-[#4f81ff] focus:ring-[#4f81ff]"
                    />
                    <span>30 天内自动登录</span>
                  </label>

                  <p className="text-right text-[#666]">
                    没有账号？
                    <button
                      type="button"
                      onClick={() => onSwitchMode("register")}
                      className="ml-1 font-medium text-[#4f81ff] transition hover:text-[#3b66db] hover:underline"
                    >
                      注册
                    </button>
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="flex h-[52px] w-full items-center justify-center rounded-[10px] bg-[linear-gradient(45deg,#4f81ff,#3b66db)] text-lg font-semibold tracking-[0.06em] text-white transition hover:-translate-y-[1px] hover:shadow-[0_8px_25px_rgba(79,129,255,0.30)] active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? "登录中..." : "登录"}
                </button>

                <div className="auth-return mt-4 flex justify-end">
                  <Link
                    className="inline-flex items-center gap-1.5 text-sm font-medium text-[#4f81ff] transition hover:text-[#3b66db] hover:underline"
                    to={APP_PATHS.cover}
                  >
                    <ArrowLeft size={15} />
                    返回封面
                  </Link>
                </div>
              </form>
            ) : (
              <form onSubmit={handleRegisterSubmit} noValidate>
                <AuthInputField
                  id="register-name"
                  label="姓名"
                  value={registerForm.full_name}
                  placeholder="请输入您的姓名"
                  autoComplete="name"
                  error={registerErrors.full_name}
                  showError={Boolean(registerErrors.full_name) && (registerTouched.full_name || registerSubmitAttempted)}
                  onBlur={() => {
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
                  error={registerErrors.account}
                  showError={Boolean(registerErrors.account) && (registerTouched.account || registerSubmitAttempted)}
                  onBlur={() => {
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
                  error={registerErrors.password}
                  showError={Boolean(registerErrors.password) && (registerTouched.password || registerSubmitAttempted)}
                  onBlur={() => {
                    setRegisterTouched((current) => ({ ...current, password: true }));
                  }}
                  onChange={(value) => setRegisterForm((current) => ({ ...current, password: value }))}
                  trailingAction={
                    <button
                      type="button"
                      aria-label={passwordVisible ? "隐藏密码" : "显示密码"}
                      onClick={onTogglePassword}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-[#98a2b3] transition hover:text-[#4f81ff]"
                    >
                      {passwordVisible ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  }
                />

                <div className="auth-options mb-6 flex justify-end text-[15px] text-[#666]">
                  <p>
                    已有账号？
                    <button
                      type="button"
                      onClick={() => onSwitchMode("login")}
                      className="ml-1 font-medium text-[#4f81ff] transition hover:text-[#3b66db] hover:underline"
                    >
                      返回登录
                    </button>
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="flex h-[52px] w-full items-center justify-center rounded-[10px] bg-[linear-gradient(45deg,#4f81ff,#3b66db)] text-lg font-semibold tracking-[0.06em] text-white transition hover:-translate-y-[1px] hover:shadow-[0_8px_25px_rgba(79,129,255,0.30)] active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? "提交中..." : "立即注册"}
                </button>

                <div className="auth-return mt-4 flex justify-end">
                  <Link
                    className="inline-flex items-center gap-1.5 text-sm font-medium text-[#4f81ff] transition hover:text-[#3b66db] hover:underline"
                    to={APP_PATHS.cover}
                  >
                    <ArrowLeft size={15} />
                    返回封面
                  </Link>
                </div>
              </form>
            )}

            <div className="auth-badges mt-9 flex items-center justify-between border-t border-[#eef2f7] pt-4 text-[13px] text-[#667084]">
              <div className="inline-flex items-center rounded-full border border-[rgba(59,130,246,0.25)] bg-[#f2f8ff] px-3 py-1 font-semibold tracking-[0.02em] text-[#3b82f6]">
                <UserRound className="auth-badge-icon" aria-hidden="true" />
                受试者端
              </div>
              <div className="flex gap-2">
                <span className="inline-flex items-center rounded-[8px] border border-[#e5e7eb] bg-[#f8fafc] px-2.5 py-1">
                  <ChartNoAxesColumn className="auth-badge-icon" aria-hidden="true" />
                  智能评估
                </span>
                <span className="inline-flex items-center rounded-[8px] border border-[#e5e7eb] bg-[#f8fafc] px-2.5 py-1">
                  <ShieldCheck className="auth-badge-icon" aria-hidden="true" />
                  安全连接
                </span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

export default AuthPage;
