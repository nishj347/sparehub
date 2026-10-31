import { apiClient } from './client';
import { Page } from '../types/common';
import {
  MachineFormData,
  MachineItem,
  MachineListParams,
  MachineOption,
} from '../types/masterData';

export const machinesApi = {
  list: async (params?: MachineListParams): Promise<Page<MachineItem>> => {
    const query = new URLSearchParams();
    if (params?.q) query.append('q', params.q);
    if (params?.status) query.append('status', params.status);
    if (params?.location_id !== undefined && params.location_id !== null) {
      query.append('location_id', params.location_id.toString());
    }
    if (params?.unassigned) query.append('unassigned', 'true');
    if (params?.sort) query.append('sort', params.sort);
    if (params?.order) query.append('order', params.order);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());

    const qs = query.toString();
    const endpoint = `/admin/machines${qs ? `?${qs}` : ''}`;
    return apiClient.get<Page<MachineItem>>(endpoint);
  },

  getOptions: async (): Promise<MachineOption[]> => {
    return apiClient.get<MachineOption[]>('/admin/machines/options');
  },

  getById: async (id: number): Promise<MachineItem> => {
    return apiClient.get<MachineItem>(`/admin/machines/${id}`);
  },

  create: async (data: MachineFormData): Promise<MachineItem> => {
    return apiClient.post<MachineItem>('/admin/machines', data);
  },

  update: async (id: number, data: Partial<MachineFormData>): Promise<MachineItem> => {
    return apiClient.patch<MachineItem>(`/admin/machines/${id}`, data);
  },

  deactivate: async (id: number): Promise<MachineItem> => {
    return apiClient.post<MachineItem>(`/admin/machines/${id}/deactivate`);
  },

  activate: async (id: number): Promise<MachineItem> => {
    return apiClient.post<MachineItem>(`/admin/machines/${id}/activate`);
  },
};

