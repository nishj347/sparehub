/**
 * Types for the Issue Part workflow (POST /api/issues) matching Module 8A backend schema.
 */

export interface IssueRequest {
  inventory_id?: number;
  part_id?: number;
  location_id?: number;
  quantity: number;
  idempotency_key: string;
  notes?: string | null;
}

export interface IssueEmployeeBrief {
  employee_id: string;
  name: string;
}

export interface IssuePartBrief {
  id: number;
  part_number: string;
  name: string;
}

export interface IssueLocationBrief {
  id: number;
  name: string;
  code: string;
}

export interface IssueResponse {
  transaction_id: number;
  issued_at: string;
  employee: IssueEmployeeBrief;
  part: IssuePartBrief;
  location: IssueLocationBrief;
  store_name: string | null;
  rack: string | null;
  bin: string | null;
  quantity_issued: number;
  quantity_remaining: number;
  message: string;
  idempotent_replay: boolean;
}

