export type UserRole = 'EMPLOYEE' | 'STORE_ADMIN';

export interface LocationBrief {
  id: number;
  name: string;
  code: string;
}

export interface CurrentUser {
  id: number;
  employee_id: string;
  name: string;
  email: string;
  role: UserRole;
  location: LocationBrief;
}

export interface LoginRequest {
  identifier: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: CurrentUser;
}

