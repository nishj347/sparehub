import { apiClient } from './client';
import { Page } from '../types/common';
import { PartCard, PartFilters, PartSearchParams } from '../types/partsPublic';

/** Build a query-string from search params, omitting empty/undefined values. */
function buildQuery(params: PartSearchParams): string {
  const p = new URLSearchParams();
  if (params.q) p.set('q', params.q);
  if (params.category) p.set('category', params.category);
  if (params.machine_id != null) p.set('machine_id', String(params.machine_id));
  if (params.location_id != null) p.set('location_id', String(params.location_id));
  if (params.availability && params.availability !== 'all') p.set('availability', params.availability);
  if (params.sort) p.set('sort', params.sort);
  if (params.order) p.set('order', params.order);
  if (params.page && params.page > 1) p.set('page', String(params.page));
  if (params.page_size && params.page_size !== 12) p.set('page_size', String(params.page_size));
  const qs = p.toString();
  return qs ? `?${qs}` : '';
}

export function searchParts(params: PartSearchParams): Promise<Page<PartCard>> {
  return apiClient.get<Page<PartCard>>(`/parts${buildQuery(params)}`);
}

export function getPartFilters(): Promise<PartFilters> {
  return apiClient.get<PartFilters>('/parts/filters');
}

