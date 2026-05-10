import type { ReactNode } from "react";

import type { UserRecord } from "../types";
import { SIDEBAR_STEPS } from "../workflow";

type ConsultationShellProps = {
  title: string;
  breadcrumb: string;
  sidebarStep: number;
  user: UserRecord;
  message?: string;
  error?: string;
  onLogout: () => void | Promise<void>;
  children: ReactNode;
};

function ConsultationShell({
  title,
  breadcrumb,
  sidebarStep,
  user,
  message,
  error,
  onLogout,
  children,
}: ConsultationShellProps) {
  return (
    <div className="consultation-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-logo">♡</div>
          <div>
            <strong>抑郁症辅助问诊系统</strong>
          </div>
        </div>

        <nav className="sidebar-nav">
          {SIDEBAR_STEPS.map((step, index) => (
            <div key={step.title} className={`sidebar-item ${sidebarStep === index ? "active" : ""}`}>
              <div className="sidebar-icon">{index + 1}</div>
              <div>
                <strong>{step.title}</strong>
                <span>{step.description}</span>
              </div>
            </div>
          ))}
        </nav>

        <div className="sidebar-help">使用指南</div>
      </aside>

      <main className="main-area">
        <header className="main-header">
          <div>
            <h1>{title}</h1>
            <p className="breadcrumb">{breadcrumb}</p>
          </div>

          <div className="header-actions">
            <div className="safety-chip">医疗级数据安全保护中</div>
            <div className="user-chip">
              <div className="avatar-circle">{user.full_name.slice(0, 1)}</div>
              <div>
                <strong>{user.full_name}</strong>
                <span>{user.id}</span>
              </div>
            </div>
            <button className="ghost-button" onClick={onLogout} type="button">
              退出
            </button>
          </div>
        </header>

        {message ? <div className="feedback-banner success">{message}</div> : null}
        {error ? (
          <div className="feedback-banner error" role="alert">
            {error}
          </div>
        ) : null}

        {children}
      </main>
    </div>
  );
}

export default ConsultationShell;
