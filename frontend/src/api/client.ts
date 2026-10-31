import { ApiErrorResponse, ApiHealthResponse, DbHealthResponse } from '../types';
import { CurrentUser, LoginRequest, LoginResponse } from '../types/auth';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/+$/, '');

// Token storage key in sessionStorage.
// DELIBERATE PROTOTYPE CHOICE: Token is stored in sessionStorage (not localStorage or cookies)
// so it clears automatically when the browser tab is closed, reducing XSS risk.
// In a production or SSO scenario, httpOnly cookies or OIDC/SAML flows would replace this approach.
const TOKEN_KEY = 'sparehub_access_token';

export class ApiError extends Error {
  public status?: number;
  public code?: string;
  public field?: string;

  constructor(message: string, status?: number, code?: string, field?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.field = field;
  }
}

// Callback registered by AuthContext to handle globally detected session expiry.
// Set at app startup — if not set, 401s just throw normally.
type SessionExpiredCallback = (message: string) => void;
let onSessionExpired: SessionExpiredCallback | null = null;

export function setSessionExpiredHandler(handler: SessionExpiredCallback): void {
  onSessionExpired = handler;
}

export function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

/**
 * Standard typed HTTP client helper for communicating with the backend REST API.
 * Automatically attaches Authorization: Bearer token from sessionStorage when present.
 * On 401 responses (excluding the login endpoint itself), triggers global session-expired flow.
 */
async function request<T>(
  endpoint: string,
  options?: RequestInit & { skipAuthRedirect?: boolean },
): Promise<T> {
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const targetUrl = `${BASE_URL}${normalizedEndpoint}`;

  const token = getStoredToken();
  const authHeader: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  let response: Response;
  try {
    response = await fetch(targetUrl, {
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...authHeader,
        ...(options?.headers || {}),
      },
      ...options,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Network request failed';
    throw new ApiError(
      `Unable to reach the server. Please try again. (${message})`,
    );
  }

  if (!response.ok) {
    let errorMessage = `HTTP error ${response.status} (${response.statusText})`;
    let errorCode: string | undefined = `HTTP_${response.status}`;
    let errorField: string | undefined = undefined;

    try {
      const errorData = (await response.json()) as ApiErrorResponse & { field?: string };
      if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        errorMessage = errorData.detail.map((item) => item.msg || JSON.stringify(item)).join('; ');
      }
      if (errorData.code) {
        errorCode = errorData.code;
      }
      if (errorData.field) {
        errorField = errorData.field;
      }
    } catch {
      // Response was not JSON; fall back to standard HTTP status message
    }

    // On 401 from any non-login endpoint, trigger session-expired flow
    const isLoginEndpoint = normalizedEndpoint === '/auth/login';
    if (response.status === 401 && !isLoginEndpoint && !options?.skipAuthRedirect) {
      clearStoredToken();
      if (onSessionExpired) {
        onSessionExpired('Your session has expired. Please sign in again.');
      }
    }

    throw new ApiError(errorMessage, response.status, errorCode, errorField);
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestInit) =>
    request<T>(endpoint, { method: 'GET', ...options }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestInit) =>
    request<T>(endpoint, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...options,
    }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestInit) =>
    request<T>(endpoint, {
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...options,
    }),

  getApiHealth: (): Promise<ApiHealthResponse> =>
    request<ApiHealthResponse>('/health'),

  getDbHealth: (): Promise<DbHealthResponse> =>
    request<DbHealthResponse>('/health/db'),

  // Authentication endpoints
  login: (payload: LoginRequest): Promise<LoginResponse> =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
      skipAuthRedirect: true,
    } as RequestInit & { skipAuthRedirect: boolean }),

  getMe: (): Promise<CurrentUser> =>
    request<CurrentUser>('/auth/me', { skipAuthRedirect: true } as RequestInit & { skipAuthRedirect: boolean }),
};
