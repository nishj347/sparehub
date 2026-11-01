import { apiClient } from './client';
import { NotificationItem, NotificationsResponse, UnreadCountResponse, ReadAllResponse } from '../types/notification';

export interface GetNotificationsParams {
  status?: 'all' | 'unread';
  unread_only?: boolean;
  page?: number;
  page_size?: number;
}

export async function getNotifications(params: GetNotificationsParams = {}): Promise<NotificationsResponse> {
  const qs = new URLSearchParams();
  const filterStatus = params.status || (params.unread_only ? 'unread' : undefined);
  if (filterStatus && filterStatus !== 'all') {
    qs.set('status', filterStatus);
  }
  if (params.page && params.page > 1) qs.set('page', String(params.page));
  if (params.page_size) qs.set('page_size', String(params.page_size));
  const query = qs.toString();
  return apiClient.get<NotificationsResponse>(`/admin/notifications${query ? `?${query}` : ''}`);
}

export async function getUnreadCount(): Promise<UnreadCountResponse> {
  return apiClient.get<UnreadCountResponse>('/admin/notifications/unread-count');
}

export async function markRead(id: number): Promise<NotificationItem> {
  return apiClient.post<NotificationItem>(`/admin/notifications/${id}/read`);
}

export async function markAllRead(): Promise<ReadAllResponse> {
  return apiClient.post<ReadAllResponse>('/admin/notifications/read-all');
}

