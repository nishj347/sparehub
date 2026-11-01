/**
 * Public (employee-facing) spare part detail types matching backend part_detail.py.
 */

export interface PublicLocationBrief {
  id: number;
  name: string;
  code: string;
  city: string;
}

export interface PublicMachineDetail {
  id: number;
  name: string;
  code: string;
  location_name: string | null;
}

export interface SpecItem {
  key: string;
  value: string;
}

export type AvailabilityStatus = 'IN_STOCK' | 'LOW_STOCK' | 'OUT_OF_STOCK';

export interface LocationStockDetail {
  inventory_id?: number;
  location: PublicLocationBrief;
  quantity: number;
  store_name: string | null;
  rack: string | null;
  bin: string | null;
  availability_status: AvailabilityStatus;
  is_my_location: boolean;
}

export interface EmployeePartDetail {
  id: number;
  part_number: string;
  name: string;
  category: string;
  manufacturer: string | null;
  description: string | null;
  image_url: string | null;
  specifications: SpecItem[];
  machines: PublicMachineDetail[];
  total_quantity: number;
  availability_status: AvailabilityStatus;
  locations: LocationStockDetail[];
}

