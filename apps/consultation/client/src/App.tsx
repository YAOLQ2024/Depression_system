import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import AuthPage from "./features/auth/AuthPage";
import { ProfileModal } from "./components/ProfileModal";
import CoverPage from "./pages/CoverPage";
import HomePage from "./pages/HomePage";
import PreparationPage from "./pages/PreparationPage";
import ConsultationPage from "./pages/ConsultationPage";
import ScaleQuestionnairePage from "./pages/ScaleQuestionnairePage";
import ResultPage from "./pages/ResultPage";
import InterventionPage from "./pages/InterventionPage";
import InterventionGamePage from "./pages/InterventionGamePage";
import InterventionStoryPage from "./pages/InterventionStoryPage";
import InterventionVideoPage from "./pages/InterventionVideoPage";
import SeamlessVideoPlayerDemoPage from "./pages/SeamlessVideoPlayerDemoPage";
import HistoryPage from "./pages/HistoryPage";
import HistoryDetailPage from "./pages/HistoryDetailPage";
import { ConsultationAppProvider } from "./app/ConsultationAppContext";
import { useConsultationApp } from "./app/useConsultationApp";
import { APP_PATHS } from "./routes";

function App() {
  const app = useConsultationApp();
  const { state, actions } = app;

  const protectedElement = (element: ReactElement) =>
    state.user ? element : <Navigate to={APP_PATHS.login} replace />;

  return (
    <ConsultationAppProvider value={app}>
      <Routes>
        <Route path={APP_PATHS.cover} element={state.user ? <Navigate to={state.postLoginPath} replace /> : <CoverPage />} />
        <Route
          path={APP_PATHS.login}
          element={
            state.user ? (
              <Navigate to={state.postLoginPath} replace />
            ) : (
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
            )
          }
        />

        <Route path={APP_PATHS.home} element={protectedElement(<HomePage />)} />
        <Route path={APP_PATHS.preparation} element={protectedElement(<PreparationPage />)} />
        <Route path={APP_PATHS.consultation} element={protectedElement(<ConsultationPage />)} />
        <Route path={APP_PATHS.assessment} element={protectedElement(<ScaleQuestionnairePage />)} />
        <Route path={APP_PATHS.result} element={protectedElement(<ResultPage />)} />
        <Route path={APP_PATHS.intervention} element={protectedElement(<InterventionPage />)} />
        <Route path={APP_PATHS.interventionVideo} element={protectedElement(<InterventionVideoPage />)} />
        <Route path={APP_PATHS.interventionGame} element={protectedElement(<InterventionGamePage />)} />
        <Route path={APP_PATHS.interventionStory} element={protectedElement(<InterventionStoryPage />)} />
        <Route path={APP_PATHS.seamlessVideoDemo} element={protectedElement(<SeamlessVideoPlayerDemoPage />)} />
        <Route path={APP_PATHS.history} element={protectedElement(<HistoryPage />)} />
        <Route path={APP_PATHS.historyDetail} element={protectedElement(<HistoryDetailPage />)} />

        <Route path="*" element={<Navigate to={state.user ? state.resumePath : APP_PATHS.cover} replace />} />
      </Routes>
      <ProfileModal />
    </ConsultationAppProvider>
  );
}

export default App;
