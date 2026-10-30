import { ApiErrorResponse, ApiHealthResponse, DbHealthResponse } from '../types';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/+$/, '');

export class ApiError extends Error {
  public status?: number;
  public code?: string;

  constructor(message: string, status?: number, code?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

/**
 * Standard typed HTTP client helper for communicating with the backend REST API.
 */
async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const targetUrl = `${BASE_URL}${normalizedEndpoint}`;

  let response: Response;
  try {
    response = await fetch(targetUrl, {
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...(options?.headers || {}),
      },
      ...options,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Network request failed';
    throw new ApiError(`Network error communicating with API (${message}). Verify backend is running.`);
  }

  if (!response.ok) {
    let errorMessage = `HTTP error ${response.status} (${response.statusText})`;
    let errorCode: string | undefined = `HTTP_${response.status}`;

    try {
      const errorData = (await response.json()) as ApiErrorResponse;
      if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        errorMessage = errorData.detail.map((item) => item.msg || JSON.stringify(item)).join('; ');
      }
      if (errorData.code) {
        errorCode = errorData.code;
      }
    } catch {
      // Response was not JSON, fallback to standard HTTP status message
    }

    throw new ApiError(errorMessage, response.status, errorCode);
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

  getApiHealth: (): Promise<ApiHealthResponse> =>
    request<ApiHealthResponse>('/health'),

  getDbHealth: (): Promise<DbHealthResponse> =>
    request<DbHealthResponse>('/health/db'),
};
