import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { DashboardPage } from '../pages/DashboardPage';
import { PlaceholderPage } from '../pages/PlaceholderPage';
import { NotFoundPage } from '../pages/NotFoundPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route
          path="parts"
          element={
            <PlaceholderPage
              title="Spare Parts Catalog"
              description="Master parts repository, cross-references, and technical specifications."
              targetModule="Module 4 (Parts Catalog & Search)"
            />
          }
        />
        <Route
          path="issues"
          element={
            <PlaceholderPage
              title="Issue History & Workflow"
              description="Historical records of spare parts issuance, requisitions, and tracking."
              targetModule="Module 6 (Issue Workflow & Audit)"
            />
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
};
