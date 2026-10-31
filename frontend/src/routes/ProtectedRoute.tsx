import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { UserRole } from '../types/auth';
import { ForbiddenPage } from '../pages/ForbiddenPage';

/**
 * Requires authentication. Unauthenticated users are redirected to /login
 * with the intended path preserved as a `from` query parameter (internal paths only).
 * Renders a neutral loading state while auth session is being restored on page load.
 */
export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-slate-400 text-sm">Loading…</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Remember where the user was trying to go so we can redirect back after login.
    // Only pass internal paths (starting with '/') to prevent open-redirect attacks.
    const intendedPath = location.pathname;
    const isInternal = intendedPath.startsWith('/') && !intendedPath.startsWith('//');
    const loginPath = isInternal ? `/login?from=${encodeURIComponent(intendedPath)}` : '/login';
    return <Navigate to={loginPath} replace />;
  }

  return <>{children}</>;
};

/**
 * Requires authentication AND one of the specified roles.
 * Renders ForbiddenPage (403) if the authenticated user lacks the required role.
 * Wraps ProtectedRoute logic so unauthenticated users still hit /login first.
 */
export const RoleRoute: React.FC<{
  allowedRoles: UserRole[];
  children: React.ReactNode;
}> = ({ allowedRoles, children }) => {
  const { user } = useAuth();

  return (
    <ProtectedRoute>
      {user && !allowedRoles.includes(user.role) ? (
        <ForbiddenPage />
      ) : (
        <>{children}</>
      )}
    </ProtectedRoute>
  );
};

