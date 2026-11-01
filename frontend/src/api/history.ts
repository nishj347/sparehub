import { apiClient } from './client';
import { MyIssuesResponse, AdminActivityResponse } from '../types/activity';

export interface GetMyIssuesParams {
  q?: string;
  location_id?: number | string;
  date_from?: string;
  date_to?: string;
  sort?: string;
  order?: string;
  page?: number;
  page_size?: number;
}

export async function getMyIssues(params: GetMyIssuesParams = {}): Promise<MyIssuesResponse> {
  const qs = new URLSearchParams();
  if (params.q) qs.set('q', params.q);
  if (params.location_id) qs.set('location_id', String(params.location_id));
  if (params.date_from) qs.set('date_from', params.date_from);
  if (params.date_to) qs.set('date_to', params.date_to);
  if (params.sort) qs.set('sort', params.sort);
  if (params.order) qs.set('order', params.order);
  if (params.page && params.page > 1) qs.set('page', String(params.page));
  if (params.page_size) qs.set('page_size', String(params.page_size));
  const query = qs.toString();
  return apiClient.get<MyIssuesResponse>(`/issues/mine${query ? `?${query}` : ''}`);
}

export interface GetAdminActivityParams {
  q?: string;
  employee?: string;
  employee_q?: string;
  type?: string;
  location_id?: number | string;
  date_from?: string;
  date_to?: string;
  sort?: string;
  order?: string;
  page?: number;
  page_size?: number;
}

export async function getAdminActivity(params: GetAdminActivityParams = {}): Promise<AdminActivityResponse> {
  const qs = new URLSearchParams();
  if (params.q) qs.set('q', params.q);
  const emp = params.employee || params.employee_q;
  if (emp) qs.set('employee', emp);
  if (params.type && params.type !== 'all') qs.set('type', params.type);
  if (params.location_id) qs.set('location_id', String(params.location_id));
  if (params.date_from) qs.set('date_from', params.date_from);
  if (params.date_to) qs.set('date_to', params.date_to);
  if (params.sort) qs.set('sort', params.sort);
  if (params.order) qs.set('order', params.order);
  if (params.page && params.page > 1) qs.set('page', String(params.page));
  if (params.page_size) qs.set('page_size', String(params.page_size));
  const query = qs.toString();
  return apiClient.get<AdminActivityResponse>(`/admin/activity${query ? `?${query}` : ''}`);
}

