import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import {
  apiClient,
  clearStoredToken,
  getStoredToken,
  setSessionExpiredHandler,
  storeToken,
} from '../api/client';
import { CurrentUser } from '../types/auth';

interface AuthContextValue {
  user: CurrentUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  sessionExpiredMessage: string | null;
  login: (identifier: string, password: string) => Promise<void>;
  logout: () => void;
  clearSessionExpiredMessage: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionExpiredMessage, setSessionExpiredMessage] = useState<string | null>(null);

  // Ref to the logout function for use inside the session-expired callback
  // without creating circular dependencies or stale closure issues.
  const logoutRef = useRef<() => void>(() => {});

  const logout = useCallback(() => {
    clearStoredToken();
    setUser(null);
    setIsLoading(false);
  }, []);

  logoutRef.current = logout;

  // Register the global 401 handler with the API client.
  // When any non-login request returns 401, this clears auth state and sets the
  // session-expired banner message so the login page can display it.
  useEffect(() => {
    setSessionExpiredHandler((message: string) => {
      logoutRef.current();
      setSessionExpiredMessage(message);
    });
  }, []);

  // On app load, attempt to restore session from stored token via /api/auth/me.
  // This prevents the login flash when the user has a valid session.
  useEffect(() => {
    const restoreSession = async () => {
      const token = getStoredToken();
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const currentUser = await apiClient.getMe();
        setUser(currentUser);
      } catch {
        // Token is invalid or expired — clean up silently
        clearStoredToken();
      } finally {
        setIsLoading(false);
      }
    };

    restoreSession();
  }, []);

  const login = useCallback(async (identifier: string, password: string): Promise<void> => {
    const response = await apiClient.login({ identifier, password });
    storeToken(response.access_token);
    setUser(response.user);
    setSessionExpiredMessage(null);
  }, []);

  const clearSessionExpiredMessage = useCallback(() => {
    setSessionExpiredMessage(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: user !== null,
        isLoading,
        sessionExpiredMessage,
        login,
        logout,
        clearSessionExpiredMessage,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}

