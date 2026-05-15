/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ConsultationPage from "./pages/ConsultationPage";
import PreparationPage from "./pages/PreparationPage";
import ScaleQuestionnairePage from "./pages/ScaleQuestionnairePage";
import ResultPage from "./pages/ResultPage";
import InterventionPage from "./pages/InterventionPage";
import { ProfileModal } from "./components/ProfileModal";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/preparation" element={<PreparationPage />} />
        <Route path="/consultation" element={<ConsultationPage />} />
        <Route path="/scale-questionnaire" element={<ScaleQuestionnairePage />} />
        <Route path="/result" element={<ResultPage />} />
        <Route path="/intervention" element={<InterventionPage />} />
      </Routes>
      <ProfileModal />
    </BrowserRouter>
  );
}
