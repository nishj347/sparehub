import { apiClient } from './client';
import { DashboardResponse } from '../types/dashboard';

export async function getAdminDashboard(): Promise<DashboardResponse> {
  return apiClient.get<DashboardResponse>('/admin/dashboard');
}

