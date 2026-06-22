import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import {
  ArrowLeft,
  Eye,
  EyeOff,
  Lock,
  User,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";

import { EntryBrand, EntryFooter, entryBackgroundStyle } from "../../components/entry-chrome";
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
  leadingIcon: LucideIcon;
  trailingAction?: ReactNode;
  error?: string;
  showError: boolean;
  onChange: (value: string) => void;
  onBlur: () => void;
  onFocus: () => void;
};

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_REGEX = /^1\d{10}$/;

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
  error,
  showError,
  onChange,
  onBlur,
  onFocus,
}: InputFieldProps) {
  return (
    <div className="space-y-1.5">
      <label className="ml-1 text-sm font-semibold tracking-[0.01em] text-slate-900" htmlFor={id}>
        {label}
      </label>
      <div className="relative">
        <LeadingIcon
          size={18}
          className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
        />
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
          className={`h-13 w-full rounded-2xl border bg-white pl-12 pr-12 text-slate-900 shadow-none outline-none transition placeholder:text-slate-400 sm:h-14 ${
            showError
              ? "border-red-300 ring-4 ring-red-100"
              : "border-slate-200 focus:border-[#315CFF] focus:ring-4 focus:ring-blue-100"
          }`}
        />
        {trailingAction}
      </div>
      {showError ? (
        <p id={`${id}-error`} className="ml-1 text-xs font-medium text-red-600" role="alert">
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
    <main className="relative min-h-[100svh] overflow-hidden bg-[#0d1631]" style={entryBackgroundStyle}>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_34%_38%,rgba(255,255,255,0.16),transparent_22%),linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02)_18%,rgba(255,255,255,0.08)_100%)]" />

      <EntryBrand />

      <div className="relative z-10 mx-auto flex min-h-[100svh] w-full max-w-[1380px] items-center justify-center px-8 py-8 lg:px-10 lg:py-10">
        <section className="relative w-full max-w-[470px]">
          <div className="absolute inset-[-58px] -z-10 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.20)_0%,rgba(255,255,255,0.09)_24%,transparent_72%)] blur-[10px]" />
          <div className="rounded-[32px] border border-white/22 bg-[linear-gradient(180deg,rgba(248,250,255,0.88),rgba(236,242,255,0.76))] p-6 pt-10 shadow-[0_28px_80px_rgba(10,18,40,0.20)] backdrop-blur-xl sm:p-8 sm:pt-12">
            <div className="mb-9">
              <h2 className="text-[2rem] font-semibold tracking-[-0.05em] text-slate-950 sm:text-[2.2rem]">
                {authMode === "login" ? "欢迎回来" : "创建新账号"}
              </h2>
              <p className="mt-2 text-sm leading-7 text-slate-500">
                {authMode === "login" ? "请输入账号与密码。" : "填写基础信息即可开始。"}
              </p>
            </div>

            {error ? (
              <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700" role="alert">
                {error}
              </div>
            ) : null}

            {authMode === "login" ? (
              <form className="space-y-4" onSubmit={handleLoginSubmit} noValidate>
                <AuthInputField
                  id="login-account"
                  label="账号"
                  value={loginForm.account}
                  placeholder="请输入 11 位手机号或邮箱"
                  autoComplete="username"
                  leadingIcon={User}
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
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-[#315CFF]"
                    >
                      {passwordVisible ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  }
                />

                <label
                  htmlFor="remember-login"
                  className="inline-flex items-center gap-3 pt-1 text-sm font-medium text-slate-400"
                >
                  <input
                    id="remember-login"
                    checked={keepLoggedIn}
                    onChange={(event) => onKeepLoggedInChange(event.target.checked)}
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-[#315CFF] focus:ring-[#315CFF]"
                  />
                  <span>30 天内自动登录</span>
                </label>

                <div className="mt-2 space-y-3">
                  <div className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-3">
                    <Link
                      className="inline-flex h-13 items-center justify-center gap-2 rounded-2xl border border-[#c8d6ff] bg-[#f4f7ff] px-5 text-sm font-semibold shadow-[0_8px_20px_rgba(37,73,214,0.08)] transition hover:border-[#9fb8ff] hover:bg-[#edf3ff] sm:h-14"
                      style={{ color: "#2448E6" }}
                      to={APP_PATHS.cover}
                    >
                      <ArrowLeft size={16} className="text-current" />
                      返回封面
                    </Link>

                    <button
                      type="submit"
                      disabled={loading}
                      className="flex h-13 min-w-0 items-center justify-center gap-2 rounded-2xl bg-[#315CFF] px-6 text-base font-semibold text-white shadow-[0_18px_40px_rgba(49,92,255,0.28)] transition hover:bg-[#2549d6] disabled:cursor-not-allowed disabled:opacity-60 sm:h-14"
                    >
                      {loading ? "登录中..." : "登 录"}
                    </button>
                  </div>

                  <div className="flex justify-end pt-1 text-sm">
                    <p className="text-slate-400">
                      还没有账号？
                      <button
                        type="button"
                        onClick={() => onSwitchMode("register")}
                        className="ml-1 font-semibold text-[#315CFF] transition hover:text-[#2549d6]"
                      >
                        立即注册
                      </button>
                    </p>
                  </div>
                </div>
              </form>
            ) : (
              <form className="space-y-4" onSubmit={handleRegisterSubmit} noValidate>
                <AuthInputField
                  id="register-name"
                  label="姓名"
                  value={registerForm.full_name}
                  placeholder="请输入您的姓名"
                  autoComplete="name"
                  leadingIcon={User}
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
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-[#315CFF]"
                    >
                      {passwordVisible ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  }
                />

                <div className="mt-2 space-y-3">
                  <div className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-3">
                    <button
                      type="button"
                      onClick={() => onSwitchMode("login")}
                      className="inline-flex h-13 items-center justify-center gap-2 rounded-2xl border border-[#c8d6ff] bg-[#f4f7ff] px-5 text-sm font-semibold shadow-[0_8px_20px_rgba(37,73,214,0.08)] transition hover:border-[#9fb8ff] hover:bg-[#edf3ff] sm:h-14"
                      style={{ color: "#2448E6" }}
                    >
                      <ArrowLeft size={16} className="text-current" />
                      取消
                    </button>

                    <button
                      type="submit"
                      disabled={loading}
                      className="flex h-13 min-w-0 items-center justify-center gap-2 rounded-2xl bg-[#315CFF] px-6 text-base font-semibold text-white shadow-[0_18px_40px_rgba(49,92,255,0.28)] transition hover:bg-[#2549d6] disabled:cursor-not-allowed disabled:opacity-60 sm:h-14"
                    >
                      {loading ? "提交中..." : "立即注册"}
                    </button>
                  </div>

                  <div className="flex justify-end pt-1 text-sm">
                    <p className="text-slate-400">
                      已有账号？
                      <button
                        type="button"
                        onClick={() => onSwitchMode("login")}
                        className="ml-1 font-semibold text-[#315CFF] transition hover:text-[#2549d6]"
                      >
                        返回登录
                      </button>
                    </p>
                  </div>
                </div>
              </form>
            )}
          </div>
        </section>
      </div>

      <EntryFooter />
    </main>
  );
}

export default AuthPage;
