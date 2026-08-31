import { Suspense, lazy, type ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

const AuthPage = lazy(() => import("./features/auth/AuthPage"));
import { ProfileModal } from "./components/ProfileModal";
const CoverPage = lazy(() => import("./pages/CoverPage"));
const HomePage = lazy(() => import("./pages/HomePage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const PreparationPage = lazy(() => import("./pages/PreparationPage"));
const ConsultationPage = lazy(() => import("./pages/ConsultationPage"));
const AssessmentSelectionPage = lazy(() => import("./pages/AssessmentSelectionPage"));
const ScaleQuestionnairePage = lazy(() => import("./pages/ScaleQuestionnairePage"));
const ResultPage = lazy(() => import("./pages/ResultPage"));
const InterventionPage = lazy(() => import("./pages/InterventionPage"));
const InterventionGamePage = lazy(() => import("./pages/InterventionGamePage"));
const InterventionStoryPage = lazy(() => import("./pages/InterventionStoryPage"));
const InterventionVideoPage = lazy(() => import("./pages/InterventionVideoPage"));
const SeamlessVideoPlayerDemoPage = lazy(() => import("./pages/SeamlessVideoPlayerDemoPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const HistoryDetailPage = lazy(() => import("./pages/HistoryDetailPage"));
const HistoryScaleDetailPage = lazy(() => import("./pages/HistoryScaleDetailPage"));
import { ConsultationAppProvider } from "./app/ConsultationAppContext";
import { useConsultationApp } from "./app/useConsultationApp";
import { APP_PATHS } from "./routes";

function RouteLoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,rgba(196,181,253,0.24),transparent_32%),linear-gradient(180deg,#eef2ff,#f8f7ff)] text-slate-600">
      <div className="rounded-full border border-white/70 bg-white/72 px-5 py-2 text-sm font-medium shadow-[0_18px_40px_rgba(129,140,248,0.14)] backdrop-blur-xl">
        正在加载页面...
      </div>
    </div>
  );
}

function App() {
  const app = useConsultationApp();
  const { state, actions } = app;

  const protectedElement = (element: ReactElement) =>
    state.user ? element : <Navigate to={APP_PATHS.login} replace />;

  const lazyPage = (element: ReactElement) => <Suspense fallback={<RouteLoadingScreen />}>{element}</Suspense>;

  return (
    <ConsultationAppProvider value={app}>
      <Routes>
        <Route
          path={APP_PATHS.cover}
          element={state.user ? <Navigate to={state.postLoginPath} replace /> : lazyPage(<CoverPage />)}
        />
        <Route
          path={APP_PATHS.login}
          element={
            state.user ? (
              <Navigate to={state.postLoginPath} replace />
            ) : (
              lazyPage(
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
                />,
              )
            )
          }
        />

        <Route path={APP_PATHS.home} element={protectedElement(lazyPage(<HomePage />))} />
        <Route path={APP_PATHS.profile} element={protectedElement(lazyPage(<ProfilePage />))} />
        <Route path={APP_PATHS.preparation} element={protectedElement(lazyPage(<PreparationPage />))} />
        <Route path={APP_PATHS.consultation} element={protectedElement(lazyPage(<ConsultationPage />))} />
        <Route path={APP_PATHS.assessmentSelection} element={protectedElement(lazyPage(<AssessmentSelectionPage />))} />
        <Route path={APP_PATHS.assessment} element={protectedElement(lazyPage(<ScaleQuestionnairePage />))} />
        <Route path={APP_PATHS.result} element={protectedElement(lazyPage(<ResultPage />))} />
        <Route path={APP_PATHS.intervention} element={protectedElement(lazyPage(<InterventionPage />))} />
        <Route path={APP_PATHS.interventionVideo} element={protectedElement(lazyPage(<InterventionVideoPage />))} />
        <Route path={APP_PATHS.interventionGame} element={protectedElement(lazyPage(<InterventionGamePage />))} />
        <Route path={APP_PATHS.interventionStory} element={protectedElement(lazyPage(<InterventionStoryPage />))} />
        <Route path={APP_PATHS.seamlessVideoDemo} element={protectedElement(lazyPage(<SeamlessVideoPlayerDemoPage />))} />
        <Route path={APP_PATHS.history} element={protectedElement(lazyPage(<HistoryPage />))} />
        <Route path={APP_PATHS.historyDetail} element={protectedElement(lazyPage(<HistoryDetailPage />))} />
        <Route path={APP_PATHS.historyScaleDetail} element={protectedElement(lazyPage(<HistoryScaleDetailPage />))} />

        <Route path="*" element={<Navigate to={state.user ? state.resumePath : APP_PATHS.cover} replace />} />
      </Routes>
      <ProfileModal />
    </ConsultationAppProvider>
  );
}

export default App;
