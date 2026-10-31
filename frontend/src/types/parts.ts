/**
 * Type definitions for Spare Parts Catalog and Inventory Stock operations.
 */

export interface MachineBrief {
  id: number;
  name: string;
  code: string;
  is_active?: boolean;
}

export interface LocationBrief {
  id: number;
  name: string;
  code: string;
}

export interface UserBrief {
  id: number;
  name: string;
  employee_id: string;
}

export interface SpecItem {
  key: string;
  value: string;
}

export interface PartListItem {
  id: number;
  part_number: string;
  name: string;
  category: string;
  manufacturer: string | null;
  image_url: string | null;
  is_active: boolean;
  total_quantity: number;
  location_count: number;
  low_stock: boolean;
  out_of_stock: boolean;
  machines: MachineBrief[];
  updated_at: string;
}

export interface InventoryItemDetail {
  id: number;
  location: LocationBrief;
  quantity: number;
  store_name: string | null;
  rack: string | null;
  bin: string | null;
  min_stock_level: number;
  low_stock: boolean;
  out_of_stock: boolean;
  updated_at: string;
}

export type TransactionType = 'RECEIVED' | 'ISSUED' | 'ADJUSTED';

export interface TransactionBrief {
  id: number;
  created_at: string;
  type: TransactionType;
  quantity_change: number;
  quantity_after: number;
  user: UserBrief | null;
  location: LocationBrief;
  notes: string | null;
}

export interface PartDetail {
  id: number;
  part_number: string;
  name: string;
  category: string;
  manufacturer: string | null;
  description: string | null;
  specifications: SpecItem[];
  image_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  total_quantity: number;
  location_count: number;
  low_stock: boolean;
  out_of_stock: boolean;
  machines: MachineBrief[];
  inventory: InventoryItemDetail[];
  recent_transactions: TransactionBrief[];
}

export interface InitialStockCreate {
  location_id: number;
  quantity: number;
  store_name?: string;
  rack?: string;
  bin?: string;
  min_stock_level?: number;
}

export interface PartCreatePayload {
  part_number: string;
  name: string;
  category: string;
  manufacturer?: string;
  description?: string;
  specifications?: SpecItem[];
  machine_ids?: number[];
  initial_stock?: InitialStockCreate;
}

export interface PartUpdatePayload {
  name?: string;
  category?: string;
  manufacturer?: string;
  description?: string;
  specifications?: SpecItem[];
  machine_ids?: number[];
}

export interface PartListParams {
  q?: string;
  category?: string;
  status?: 'active' | 'inactive' | 'all';
  stock?: 'all' | 'in_stock' | 'low' | 'out';
  location_id?: number;
  machine_id?: number;
  sort?: 'name' | 'part_number' | 'category' | 'total_quantity' | 'updated_at';
  order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface InventoryAddLocationPayload {
  location_id: number;
  quantity: number;
  store_name?: string;
  rack?: string;
  bin?: string;
  min_stock_level?: number;
}

export interface InventoryUpdatePayload {
  store_name?: string;
  rack?: string;
  bin?: string;
  min_stock_level?: number;
}

export interface StockReceivePayload {
  quantity: number;
  notes?: string;
}

export interface StockAdjustPayload {
  new_quantity: number;
  notes: string;
}

export interface InventoryRead {
  id: number;
  part_id: number;
  location_id: number;
  location: LocationBrief;
  quantity: number;
  store_name: string | null;
  rack: string | null;
  bin: string | null;
  min_stock_level: number;
  low_stock: boolean;
  out_of_stock: boolean;
  updated_at: string;
}

