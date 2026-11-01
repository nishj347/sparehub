// Types matching backend/app/schemas/dashboard.py

export interface DashboardStats {
  total_parts: number;
  total_units: number;
  low_stock_parts: number;
  out_of_stock_parts: number;
  todays_issues: number;
  todays_units_issued: number;
}

export interface DashboardPartBrief {
  id: number;
  part_number: string;
  name: string;
}

export interface DashboardLocationBrief {
  id: number;
  name: string;
  code: string;
}

export interface DashboardActor {
  employee_id: string;
  name: string;
}

export interface DashboardActivityItem {
  id: number;
  created_at: string;
  type: string; // ISSUED | RECEIVED | ADJUSTED
  quantity_change: number; // Signed delta
  part: DashboardPartBrief;
  location: DashboardLocationBrief;
  actor: DashboardActor | null;
}

export interface DashboardLowStockPart {
  id: number;
  part_number: string;
  name: string;
  image_url: string | null;
}

export interface DashboardLowStockItem {
  inventory_id: number;
  part: DashboardLowStockPart;
  location: DashboardLocationBrief;
  quantity: number;
  min_stock_level: number;
  shortfall: number;
}

export interface DashboardResponse {
  stats: DashboardStats;
  recent_activity: DashboardActivityItem[];
  low_stock_items: DashboardLowStockItem[];
  low_stock_total: number;
  generated_at: string;
}

