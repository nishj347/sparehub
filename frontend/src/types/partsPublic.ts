/**
 * Public (employee-facing) spare-part types matching backend part_public.py exactly.
 * other_locations_with_stock is an integer count (not an array).
 */

export interface PublicLocationBrief {
  id: number;
  name: string;
  code: string;
}

export interface PublicMachineBrief {
  id: number;
  name: string;
  code: string;
}

export interface PrimaryLocation {
  location: PublicLocationBrief;
  quantity: number;
  store_name: string | null;
  rack: string | null;
  bin: string | null;
  is_my_location: boolean;
}

export type AvailabilityStatus = 'IN_STOCK' | 'LOW_STOCK' | 'OUT_OF_STOCK';

export interface PartCard {
  id: number;
  part_number: string;
  name: string;
  category: string;
  manufacturer: string | null;
  short_description: string | null;
  image_url: string | null;
  machines: PublicMachineBrief[];
  machine_count_total: number;
  total_quantity: number;
  location_count_with_stock: number;
  availability_status: AvailabilityStatus;
  primary_location: PrimaryLocation | null;
  other_locations_with_stock: number; // integer count
}

export interface PartFilters {
  categories: string[];
  machines: PublicMachineBrief[];
  locations: PublicLocationBrief[];
}

export interface PartSearchParams {
  q?: string;
  category?: string;
  machine_id?: number;
  location_id?: number;
  availability?: 'all' | 'available' | 'my_location' | 'location';
  sort?: 'relevance' | 'name' | 'part_number' | 'availability';
  order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

