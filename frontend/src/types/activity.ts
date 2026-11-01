// Types matching backend/app/schemas/activity.py

export interface MyIssuePartBrief {
  id: number;
  part_number: string;
  name: string;
  image_url: string | null;
}

export interface MyIssueLocationBrief {
  id: number;
  name: string;
  code: string;
}

export interface MyIssueItem {
  transaction_id: number;
  created_at: string;
  part: MyIssuePartBrief;
  quantity: number; // always positive — units issued
  location: MyIssueLocationBrief;
  notes: string | null;
}

export interface IssueSummary {
  total_issues: number;
  total_units: number;
}

export interface MyIssuesResponse {
  items: MyIssueItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary: IssueSummary;
}

// ---- Admin Activity ----

export interface ActivityActor {
  user_id: number;
  employee_id: string;
  name: string;
  role: string;
}

export interface AdminActivityPartBrief {
  id: number;
  part_number: string;
  name: string;
}

export interface AdminActivityLocationBrief {
  id: number;
  name: string;
  code: string;
}

export interface AdminActivityItem {
  id: number;
  created_at: string;
  type: 'ISSUED' | 'RECEIVED' | 'ADJUSTED';
  quantity_change: number; // signed: negative for ISSUED
  quantity_after: number;
  part: AdminActivityPartBrief;
  location: AdminActivityLocationBrief;
  actor: ActivityActor | null;
  notes: string | null;
}

export interface AdminActivitySummary {
  total_rows: number;
  units_issued: number;
  units_received: number;
}

export interface AdminActivityResponse {
  items: AdminActivityItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary: AdminActivitySummary;
}

