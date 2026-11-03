import { UserRole } from './auth';

export interface UserLocationBrief {
  id: number;
  name: string;
  code: string;
}

export interface UserListItem {
  id: number;
  employee_id: string;
  name: string;
  email: string;
  role: UserRole;
  location: UserLocationBrief;
  is_active: boolean;
  is_locked: boolean;
  created_at: string;
}

export interface UserCreatePayload {
  employee_id: string;
  name: string;
  email: string;
  role: UserRole;
  location_id: number;
  password: string;
}

export interface UserUpdatePayload {
  name?: string;
  email?: string;
  role?: UserRole;
  location_id?: number;
}

export interface UserPasswordResetPayload {
  password: string;
}

export interface UserListParams {
  q?: string;
  role?: string;
  location_id?: number;
  status?: 'active' | 'inactive' | 'all';
  sort?: 'employee_id' | 'name' | 'created_at';
  order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

