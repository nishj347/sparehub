// Types matching backend/app/schemas/notification.py

export interface NotificationItem {
  id: number;
  message: string;
  is_read: boolean;
  created_at: string;
  transaction_id: number | null;
  part_id: number | null;
  part_name: string | null;
  quantity: number | null;
  actor_employee_id: string | null;
}

export interface NotificationsResponse {
  items: NotificationItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UnreadCountResponse {
  unread: number;
}

export interface ReadAllResponse {
  updated: number;
}

