/**
 * Master Data types for Locations and Machines.
 */

export interface LocationItem {
  id: number;
  name: string;
  code: string;
  city: string;
  is_active: boolean;
  created_at: string;
  user_count: number;
  machine_count: number;
  stocked_part_count: number;
}

export interface LocationOption {
  id: number;
  name: string;
  code: string;
}

export interface LocationFormData {
  name: string;
  code: string;
  city: string;
}

export interface LocationListParams {
  q?: string;
  status?: 'active' | 'inactive' | 'all';
  sort?: string;
  order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface MachineLocationBrief {
  id: number;
  name: string;
  code: string;
}

export interface MachineItem {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
  created_at: string;
  location: MachineLocationBrief | null;
  part_count: number;
}

export interface MachineOption {
  id: number;
  name: string;
  code: string;
}

export interface MachineFormData {
  name: string;
  code: string;
  location_id: number | null;
}

export interface MachineListParams {
  q?: string;
  status?: 'active' | 'inactive' | 'all';
  location_id?: number;
  unassigned?: boolean;
  sort?: string;
  order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

