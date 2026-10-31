import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Lock, ShieldCheck, User } from 'lucide-react';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, isLoading, user, sessionExpiredMessage, clearSessionExpiredMessage } =
    useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const identifierRef = useRef<HTMLInputElement>(null);

  // Prevent open-redirect: only allow internal absolute paths
  const getIntendedDestination = (): string => {
    const params = new URLSearchParams(location.search);
    const from = params.get('from');
    if (from && from.startsWith('/') && !from.startsWith('//')) {
      return from;
    }
    return null as unknown as string;
  };

  // If already authenticated, redirect away from login page
  useEffect(() => {
    if (!isLoading && isAuthenticated && user) {
      const intended = getIntendedDestination();
      if (intended) {
        navigate(intended, { replace: true });
      } else {
        navigate(user.role === 'STORE_ADMIN' ? '/admin' : '/', { replace: true });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, isLoading, user]);

  useEffect(() => {
    identifierRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    clearSessionExpiredMessage();

    if (!identifier.trim() || !password) {
      setErrorMessage('Please enter your Employee ID or Email and Password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login(identifier.trim(), password);
      // Navigation handled by the useEffect above on user state change
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.code === 'invalid_credentials' || err.status === 401) {
          setErrorMessage('Invalid credentials. Please check your Employee ID or email and password.');
        } else if (!err.status) {
          // Network error — no status code set
          setErrorMessage('Unable to reach the server. Please try again.');
        } else {
          setErrorMessage(err.message || 'Login failed. Please try again.');
        }
      } else {
        setErrorMessage('Unable to reach the server. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-slate-500 text-sm">Loading…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Brand header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-600 mb-4">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold text-slate-900">Spare Parts Management</h1>
          <p className="mt-1 text-sm text-slate-500">Enterprise Catalog · Internal Platform</p>
        </div>

        {/* Session expired banner */}
        {sessionExpiredMessage && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
            {sessionExpiredMessage}
          </div>
        )}

        {/* Login card */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8">
          <h2 className="text-base font-semibold text-slate-800 mb-6">Sign in to your account</h2>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Employee ID / Email */}
            <div>
              <label
                htmlFor="identifier"
                className="block text-xs font-medium text-slate-600 mb-1.5"
              >
                Employee ID or Email
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                  <User className="w-4 h-4" />
                </span>
                <input
                  ref={identifierRef}
                  id="identifier"
                  type="text"
                  autoComplete="username"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  disabled={isSubmitting}
                  placeholder="e.g. ITC10452 or name@example.test"
                  className="w-full pl-9 pr-3 py-2.5 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="password"
                className="block text-xs font-medium text-slate-600 mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                  <Lock className="w-4 h-4" />
                </span>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-10 py-2.5 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60 disabled:cursor-not-allowed"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Inline error */}
            {errorMessage && (
              <p role="alert" className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {errorMessage}
              </p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          Internal access only. Contact your administrator if you have login issues.
        </p>
      </div>
    </div>
  );
};

