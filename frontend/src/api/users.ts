import { apiClient } from './client';
import { Page } from '../types/common';
import {
  UserCreatePayload,
  UserListItem,
  UserListParams,
  UserPasswordResetPayload,
  UserUpdatePayload,
} from '../types/user';

export const usersApi = {
  list: async (params?: UserListParams): Promise<Page<UserListItem>> => {
    const query = new URLSearchParams();
    if (params?.q) query.append('q', params.q);
    if (params?.role) query.append('role', params.role);
    if (params?.location_id != null) query.append('location_id', params.location_id.toString());
    if (params?.status) query.append('status', params.status);
    if (params?.sort) query.append('sort', params.sort);
    if (params?.order) query.append('order', params.order);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());

    const qs = query.toString();
    const endpoint = `/admin/users${qs ? `?${qs}` : ''}`;
    return apiClient.get<Page<UserListItem>>(endpoint);
  },

  create: async (data: UserCreatePayload): Promise<UserListItem> => {
    return apiClient.post<UserListItem>('/admin/users', data);
  },

  update: async (id: number, data: UserUpdatePayload): Promise<UserListItem> => {
    return apiClient.patch<UserListItem>(`/admin/users/${id}`, data);
  },

  deactivate: async (id: number): Promise<UserListItem> => {
    return apiClient.post<UserListItem>(`/admin/users/${id}/deactivate`);
  },

  activate: async (id: number): Promise<UserListItem> => {
    return apiClient.post<UserListItem>(`/admin/users/${id}/activate`);
  },

  resetPassword: async (id: number, data: UserPasswordResetPayload): Promise<UserListItem> => {
    return apiClient.post<UserListItem>(`/admin/users/${id}/reset-password`, data);
  },
};

