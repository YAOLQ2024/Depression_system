/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import AppShell from './components/layout/AppShell';
import AuthPage from './pages/AuthPage';
import PreparationPage from './pages/PreparationPage';
import ConsultationPage from './pages/ConsultationPage';
import AssessmentPage from './pages/AssessmentPage';
import ResultPage from './pages/ResultPage';
import { PageState } from './types';
import { mockUser } from './mockData';

export default function App() {
  const [currentPage, setCurrentPage] = useState<PageState>('auth');

  const handleLogin = () => setCurrentPage('preparation');
  const handleStartConsultation = () => setCurrentPage('consultation');
  const handleGoToAssessment = () => setCurrentPage('assessment');
  const handleAssessmentComplete = () => setCurrentPage('result');
  const handleRestart = () => setCurrentPage('preparation');

  const renderContent = () => {
    switch (currentPage) {
      case 'auth':
        return <AuthPage onLogin={handleLogin} />;
      case 'preparation':
        return <PreparationPage onStart={handleStartConsultation} />;
      case 'consultation':
        return <ConsultationPage onComplete={handleGoToAssessment} />;
      case 'assessment':
        return <AssessmentPage onComplete={handleAssessmentComplete} />;
      case 'result':
        return <ResultPage onRestart={handleRestart} />;
      default:
        return <AuthPage onLogin={handleLogin} />;
    }
  };

  return (
    <AppShell 
      currentPage={currentPage} 
      onPageChange={setCurrentPage} 
      user={mockUser}
    >
      {renderContent()}
    </AppShell>
  );
}
