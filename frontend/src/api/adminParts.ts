import { apiClient } from './client';
import { Page } from '../types/common';
import {
  InventoryAddLocationPayload,
  InventoryRead,
  InventoryUpdatePayload,
  PartCreatePayload,
  PartDetail,
  PartListItem,
  PartListParams,
  PartUpdatePayload,
  StockAdjustPayload,
  StockReceivePayload,
} from '../types/parts';

export const adminPartsApi = {
  list: async (params?: PartListParams): Promise<Page<PartListItem>> => {
    const query = new URLSearchParams();
    if (params?.q) query.append('q', params.q);
    if (params?.category) query.append('category', params.category);
    if (params?.status) query.append('status', params.status);
    if (params?.stock) query.append('stock', params.stock);
    if (params?.location_id !== undefined && params.location_id !== null) {
      query.append('location_id', params.location_id.toString());
    }
    if (params?.machine_id !== undefined && params.machine_id !== null) {
      query.append('machine_id', params.machine_id.toString());
    }
    if (params?.sort) query.append('sort', params.sort);
    if (params?.order) query.append('order', params.order);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());

    const qs = query.toString();
    const endpoint = `/admin/parts${qs ? `?${qs}` : ''}`;
    return apiClient.get<Page<PartListItem>>(endpoint);
  },

  getCategories: async (): Promise<string[]> => {
    return apiClient.get<string[]>('/admin/parts/categories');
  },

  getById: async (id: number): Promise<PartDetail> => {
    return apiClient.get<PartDetail>(`/admin/parts/${id}`);
  },

  create: async (data: PartCreatePayload): Promise<PartDetail> => {
    return apiClient.post<PartDetail>('/admin/parts', data);
  },

  update: async (id: number, data: PartUpdatePayload): Promise<PartDetail> => {
    return apiClient.patch<PartDetail>(`/admin/parts/${id}`, data);
  },

  uploadImage: async (id: number, file: File): Promise<PartDetail> => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post<PartDetail>(`/admin/parts/${id}/image`, formData);
  },

  deleteImage: async (id: number): Promise<PartDetail> => {
    return apiClient.delete<PartDetail>(`/admin/parts/${id}/image`);
  },

  deactivate: async (id: number): Promise<PartDetail> => {
    return apiClient.post<PartDetail>(`/admin/parts/${id}/deactivate`);
  },

  activate: async (id: number): Promise<PartDetail> => {
    return apiClient.post<PartDetail>(`/admin/parts/${id}/activate`);
  },

  addLocation: async (partId: number, data: InventoryAddLocationPayload): Promise<InventoryRead> => {
    return apiClient.post<InventoryRead>(`/admin/parts/${partId}/inventory`, data);
  },

  updateInventory: async (inventoryId: number, data: InventoryUpdatePayload): Promise<InventoryRead> => {
    return apiClient.patch<InventoryRead>(`/admin/inventory/${inventoryId}`, data);
  },

  receiveStock: async (inventoryId: number, data: StockReceivePayload): Promise<InventoryRead> => {
    return apiClient.post<InventoryRead>(`/admin/inventory/${inventoryId}/receive`, data);
  },

  adjustStock: async (inventoryId: number, data: StockAdjustPayload): Promise<InventoryRead> => {
    return apiClient.post<InventoryRead>(`/admin/inventory/${inventoryId}/adjust`, data);
  },
};

