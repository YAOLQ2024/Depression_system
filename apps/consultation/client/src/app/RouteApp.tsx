import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useEffect } from "react";

import ConsultationShell from "../layouts/ConsultationShell";
import { APP_PATHS, isPublicPath } from "../routes";
import AssessmentPage from "../pages/AssessmentPage";
import ConsultationEntryPage from "../pages/ConsultationEntryPage";
import ConsultationPage from "../pages/ConsultationPage";
import CoverPage from "../pages/CoverPage";
import PreparationPage from "../pages/PreparationPage";
import ResultPage from "../pages/ResultPage";
import AuthPage from "../features/auth/AuthPage";
import { useConsultationApp } from "./useConsultationApp";

function RouteApp() {
  const navigate = useNavigate();
  const location = useLocation();
  const { state, actions } = useConsultationApp();

  useEffect(() => {
    if (!state.user && isPublicPath(location.pathname)) {
      return;
    }

    if (location.pathname !== state.resolvedPath) {
      navigate(state.resolvedPath, { replace: true });
    }
  }, [location.pathname, navigate, state.resolvedPath, state.user]);

  return (
    <Routes>
      <Route path={APP_PATHS.cover} element={state.user ? <Navigate to={state.resolvedPath} replace /> : <CoverPage />} />
      <Route
        path={APP_PATHS.login}
        element={
          <AuthPage
            authMode={state.authMode}
            passwordVisible={state.passwordVisible}
            keepLoggedIn={state.keepLoggedIn}
            loading={state.loading}
            error={state.error}
            onSwitchMode={(mode) => {
              actions.resetFeedback();
              actions.setAuthMode(mode);
            }}
            onTogglePassword={() => actions.setPasswordVisible((current) => !current)}
            onKeepLoggedInChange={actions.handleKeepLoggedInChange}
            onLogin={actions.handleLogin}
            onRegister={actions.handleRegister}
          />
        }
      />
      <Route
        path={APP_PATHS.preparation}
        element={
          state.user ? (
            <ConsultationShell
              breadcrumb="患者端主链"
              error={state.error}
              message={state.message}
              onLogout={() => void actions.handleLogout()}
              sidebarStep={0}
              title="问诊准备"
              user={state.user}
            >
              <PreparationPage loading={state.loading} onSubmit={actions.handlePreparationSave} user={state.user} />
            </ConsultationShell>
          ) : (
            <Navigate to={state.resolvedPath} replace />
          )
        }
      />
      <Route
        path={APP_PATHS.consultationEntry}
        element={
          state.user ? (
            <ConsultationShell
              breadcrumb="患者端主链"
              error={state.error}
              message={state.message}
              onLogout={() => void actions.handleLogout()}
              sidebarStep={0}
              title="正式问诊入口"
              user={state.user}
            >
              <ConsultationEntryPage loading={state.loading} onStart={actions.handleStartConsultation} />
            </ConsultationShell>
          ) : (
            <Navigate to={state.resolvedPath} replace />
          )
        }
      />
      <Route
        path={APP_PATHS.consultation}
        element={
          state.user && state.consultation ? (
            <ConsultationShell
              breadcrumb="AI 数字医生交互"
              error={state.error}
              message={state.message}
              onLogout={() => void actions.handleLogout()}
              sidebarStep={1}
              title="数字人问诊"
              user={state.user}
            >
              <ConsultationPage
                bootstrap={state.bootstrap}
                consultation={state.consultation}
                consultationInput={state.consultationInput}
                loading={state.loading}
                onConsultationInputChange={actions.setConsultationInput}
                onRefresh={actions.refreshConsultation}
                onStartAssessment={actions.handleStartAssessment}
                onSubmitManualTurn={actions.submitManualConsultationTurn}
                onSubmitTurn={actions.submitConsultationTurn}
              />
            </ConsultationShell>
          ) : (
            <Navigate to={state.resolvedPath} replace />
          )
        }
      />
      <Route
        path={APP_PATHS.assessment}
        element={
          state.user && state.assessment ? (
            <ConsultationShell
              breadcrumb={state.currentScaleMeta?.name || "量表问诊"}
              error={state.error}
              message={state.message}
              onLogout={() => void actions.handleLogout()}
              sidebarStep={2}
              title={`${state.currentScaleMeta?.short_name || state.assessment.current_scale_slug || "量表"} 量表问诊`}
              user={state.user}
            >
              <AssessmentPage
                assessment={state.assessment}
                assessmentCatalog={state.assessmentCatalog}
                assessmentRawInput={state.assessmentRawInput}
                loading={state.loading}
                onAssessmentRawInputChange={actions.setAssessmentRawInput}
                onRefresh={actions.refreshAssessment}
                onSelectAssessmentScore={actions.setSelectedAssessmentScore}
                onSubmit={actions.handleSubmitAssessment}
                selectedAssessmentScore={state.selectedAssessmentScore}
              />
            </ConsultationShell>
          ) : (
            <Navigate to={state.resolvedPath} replace />
          )
        }
      />
      <Route
        path={APP_PATHS.result}
        element={
          state.user && state.assessment ? (
            <ConsultationShell
              breadcrumb="评估结果与建议"
              error={state.error}
              message={state.message}
              onLogout={() => void actions.handleLogout()}
              sidebarStep={3}
              title="结果分析"
              user={state.user}
            >
              <ResultPage
                assessment={state.assessment}
                assessmentCatalog={state.assessmentCatalog}
                onRefresh={actions.refreshAssessment}
              />
            </ConsultationShell>
          ) : (
            <Navigate to={state.resolvedPath} replace />
          )
        }
      />
      <Route path="*" element={<Navigate to={state.resolvedPath} replace />} />
    </Routes>
  );
}

export default RouteApp;
