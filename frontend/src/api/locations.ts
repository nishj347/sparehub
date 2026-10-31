import { apiClient } from './client';
import { Page } from '../types/common';
import {
  LocationFormData,
  LocationItem,
  LocationListParams,
  LocationOption,
} from '../types/masterData';

export const locationsApi = {
  list: async (params?: LocationListParams): Promise<Page<LocationItem>> => {
    const query = new URLSearchParams();
    if (params?.q) query.append('q', params.q);
    if (params?.status) query.append('status', params.status);
    if (params?.sort) query.append('sort', params.sort);
    if (params?.order) query.append('order', params.order);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());

    const qs = query.toString();
    const endpoint = `/admin/locations${qs ? `?${qs}` : ''}`;
    return apiClient.get<Page<LocationItem>>(endpoint);
  },

  getOptions: async (): Promise<LocationOption[]> => {
    return apiClient.get<LocationOption[]>('/admin/locations/options');
  },

  getById: async (id: number): Promise<LocationItem> => {
    return apiClient.get<LocationItem>(`/admin/locations/${id}`);
  },

  create: async (data: LocationFormData): Promise<LocationItem> => {
    return apiClient.post<LocationItem>('/admin/locations', data);
  },

  update: async (id: number, data: Partial<LocationFormData>): Promise<LocationItem> => {
    return apiClient.patch<LocationItem>(`/admin/locations/${id}`, data);
  },

  deactivate: async (id: number): Promise<LocationItem> => {
    return apiClient.post<LocationItem>(`/admin/locations/${id}/deactivate`);
  },

  activate: async (id: number): Promise<LocationItem> => {
    return apiClient.post<LocationItem>(`/admin/locations/${id}/activate`);
  },
};

