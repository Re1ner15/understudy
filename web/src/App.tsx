import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { TopBar } from './components/TopBar';
import { MeetingView } from './views/MeetingView';
import { CommitmentsView } from './views/CommitmentsView';
import { MinutesView } from './views/MinutesView';
import { CompanionView } from './views/CompanionView';
import { AuditView } from './views/AuditView';
import { HistoryView } from './views/HistoryView';

const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="app" style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <TopBar />
      {children}
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <Routes>
        <Route
          path="/"
          element={
            <MainLayout>
              <MeetingView />
            </MainLayout>
          }
        />
        <Route
          path="/meeting"
          element={
            <MainLayout>
              <MeetingView />
            </MainLayout>
          }
        />
        <Route
          path="/commitments"
          element={
            <MainLayout>
              <CommitmentsView />
            </MainLayout>
          }
        />
        <Route
          path="/minutes"
          element={
            <MainLayout>
              <MinutesView />
            </MainLayout>
          }
        />
        <Route
          path="/audit"
          element={
            <MainLayout>
              <AuditView />
            </MainLayout>
          }
        />
        <Route
          path="/history"
          element={
            <MainLayout>
              <HistoryView />
            </MainLayout>
          }
        />
        <Route path="/companion" element={<CompanionView />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

