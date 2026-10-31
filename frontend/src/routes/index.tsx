import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { DashboardPage } from '../pages/employee/DashboardPage';
import { PartsSearchPage } from '../pages/employee/PartsSearchPage';
import { PartDetailPlaceholder } from '../pages/employee/PartDetailPlaceholder';
import { ForbiddenPage } from '../pages/ForbiddenPage';
import { LoginPage } from '../pages/LoginPage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { PlaceholderPage } from '../pages/PlaceholderPage';
import { LocationsPage } from '../pages/admin/LocationsPage';
import { MachinesPage } from '../pages/admin/MachinesPage';
import { PartsPage } from '../pages/admin/PartsPage';
import { PartCreatePage } from '../pages/admin/PartCreatePage';
import { PartEditPage } from '../pages/admin/PartEditPage';
import { PartDetailPage } from '../pages/admin/PartDetailPage';
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
        <Route path="parts/:id" element={<PartDetailPlaceholder />} />
        <Route
          path="issues"
          element={
            <PlaceholderPage
              title="My Issue History"
              description="Historical records of spare parts issuance and tracking."
              targetModule="Module 7 (Issue Workflow & Audit)"
            />
          }
        />
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
        <Route
          index
          element={
            <PlaceholderPage
              title="Admin Dashboard"
              description="Overview of inventory levels, recent transactions, and low-stock alerts."
              targetModule="Module 4 (Admin Dashboard)"
            />
          }
        />
        <Route path="locations" element={<LocationsPage />} />
        <Route path="machines" element={<MachinesPage />} />
        <Route path="parts" element={<PartsPage />} />
        <Route path="parts/new" element={<PartCreatePage />} />
        <Route path="parts/:id" element={<PartDetailPage />} />
        <Route path="parts/:id/edit" element={<PartEditPage />} />
        <Route path="inventory" element={<Navigate to="/admin/parts" replace />} />
        <Route
          path="activity"
          element={
            <PlaceholderPage
              title="Inventory Activity"
              description="Ledger of all inventory transactions — received, issued, and adjusted."
              targetModule="Module 5 (Inventory Activity Log)"
            />
          }
        />
        <Route
          path="notifications"
          element={
            <PlaceholderPage
              title="Notifications"
              description="Low-stock alerts and system notifications for store administrators."
              targetModule="Module 7 (Notifications)"
            />
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      {/* Explicit 403 page */}
      <Route path="/forbidden" element={<ForbiddenPage />} />

      {/* Catch-all 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};

