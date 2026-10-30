export interface ApiHealthResponse {
  status: string;
  environment: string;
}

export interface DbHealthResponse {
  status: string;
  database: string;
}

export interface ApiErrorResponse {
  detail: string | Array<{ msg: string; loc?: string[] }>;
  code?: string;
}

export type HealthCheckStatus = 'idle' | 'loading' | 'success' | 'error';

export interface SystemStatusState {
  apiStatus: HealthCheckStatus;
  dbStatus: HealthCheckStatus;
  environment?: string;
  apiError?: string;
  dbError?: string;
  lastChecked?: Date;
}
