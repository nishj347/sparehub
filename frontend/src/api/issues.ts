/**
 * Issue part API endpoint client helper.
 */
import { apiClient } from './client';
import { IssueRequest, IssueResponse } from '../types/issues';

/**
 * Issue a spare part atomically.
 * POST /api/issues
 */
export async function createIssue(data: IssueRequest): Promise<IssueResponse> {
  return apiClient.post<IssueResponse>('/issues', data);
}

