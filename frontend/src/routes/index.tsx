import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { DashboardPage } from '../pages/employee/DashboardPage';
import { PartsSearchPage } from '../pages/employee/PartsSearchPage';
import { PartDetailPage as EmployeePartDetailPage } from '../pages/employee/PartDetailPage';
import { IssueHistoryPage } from '../pages/employee/IssueHistoryPage';
import { ForbiddenPage } from '../pages/ForbiddenPage';
import { LoginPage } from '../pages/LoginPage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { LocationsPage } from '../pages/admin/LocationsPage';
import { MachinesPage } from '../pages/admin/MachinesPage';
import { PartsPage } from '../pages/admin/PartsPage';
import { PartCreatePage } from '../pages/admin/PartCreatePage';
import { PartEditPage } from '../pages/admin/PartEditPage';
import { PartDetailPage } from '../pages/admin/PartDetailPage';
import { ActivityPage } from '../pages/admin/ActivityPage';
import { NotificationsPage } from '../pages/admin/NotificationsPage';
import { AdminDashboardPage } from '../pages/admin/AdminDashboardPage';
import { ProtectedRoute, RoleRoute } from './ProtectedRoute';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />

      {/* Employee area — accessible by both EMPLOYEE and STORE_ADMIN */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="parts" element={<PartsSearchPage />} />
        <Route path="parts/:id" element={<EmployeePartDetailPage />} />
        <Route path="history" element={<IssueHistoryPage />} />
        <Route path="issues" element={<Navigate to="/history" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      {/* Admin area — STORE_ADMIN only */}
      <Route
        path="/admin"
        element={
          <RoleRoute allowedRoles={['STORE_ADMIN']}>
            <AppShell />
          </RoleRoute>
        }
      >
        <Route index element={<AdminDashboardPage />} />
        <Route path="locations" element={<LocationsPage />} />
        <Route path="machines" element={<MachinesPage />} />
        <Route path="parts" element={<PartsPage />} />
        <Route path="parts/new" element={<PartCreatePage />} />
        <Route path="parts/:id" element={<PartDetailPage />} />
        <Route path="parts/:id/edit" element={<PartEditPage />} />
        <Route path="inventory" element={<Navigate to="/admin/parts" replace />} />
        <Route path="activity" element={<ActivityPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      {/* Explicit 403 page */}
      <Route path="/forbidden" element={<ForbiddenPage />} />

      {/* Catch-all 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};

