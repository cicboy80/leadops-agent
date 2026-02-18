import type {
  Lead,
  LeadListResponse,
  EmailDraft,
  ActivityLog,
  Feedback,
  ScoringConfig,
  HealthResponse,
  UploadResponse,
  PipelineRunResponse,
  DashboardStats,
  OutcomeStageRecord,
  NextStagesResponse,
  ReplyClassification,
  InboundReplyResponse,
  Notification,
} from './types';

// Server-side (SSR): call backend directly via BACKEND_URL (runtime env)
// Client-side (browser): call /api/v1 which Next.js API route proxies to backend
function getApiUrl(): string {
  if (typeof window === 'undefined') {
    return `${process.env.BACKEND_URL || 'http://localhost:8000'}/api/v1`;
  }
  return '/api/v1';
}

// Server-side: use real API key. Client-side: proxy injects it server-side
function getApiKey(): string {
  if (typeof window === 'undefined') {
    return process.env.API_KEY || 'dev-api-key-change-me';
  }
  return 'proxied'; // placeholder — proxy route injects the real key
}

// Server-side: read demo-session cookie for SSR requests to backend
function getDemoSessionHeader(): Record<string, string> {
  if (typeof window === 'undefined') {
    try {
      // Dynamic import inside try — next/headers only works in server components
      const { cookies } = require('next/headers');
      const cookieStore = cookies();
      const sessionId = cookieStore.get('demo-session')?.value;
      if (sessionId) {
        return { 'X-Demo-Session': sessionId };
      }
    } catch {
      // Not in a server component context — skip
    }
  }
  return {};
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${getApiUrl()}${path}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': getApiKey(),
      ...getDemoSessionHeader(),
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorMessage = `API request failed: ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      // Ignore JSON parse errors
    }
    throw new ApiError(response.status, errorMessage);
  }

  return response.json();
}

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health');
}

export async function getLeads(params?: {
  cursor?: string;
  limit?: number;
  score_label?: string;
  status?: string;
  outcome_stage?: string;
}): Promise<LeadListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.cursor) searchParams.set('cursor', params.cursor);
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.score_label) searchParams.set('score_label', params.score_label);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.outcome_stage) searchParams.set('outcome_stage', params.outcome_stage);

  const query = searchParams.toString();
  return apiFetch<LeadListResponse>(`/leads${query ? `?${query}` : ''}`);
}

export async function getLead(leadId: string): Promise<Lead> {
  return apiFetch<Lead>(`/leads/${leadId}`);
}

export async function uploadCSV(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${getApiUrl()}/leads/upload`, {
    method: 'POST',
    headers: {
      'X-API-Key': getApiKey(),
      ...getDemoSessionHeader(),
    },
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = `Upload failed: ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      // Ignore JSON parse errors
    }
    throw new ApiError(response.status, errorMessage);
  }

  return response.json();
}

export async function runPipeline(leadId: string): Promise<PipelineRunResponse> {
  return apiFetch<PipelineRunResponse>(`/leads/${leadId}/run`, {
    method: 'POST',
  });
}

export async function bulkRunPipeline(leadIds: string[]): Promise<{ pipeline_runs: PipelineRunResponse[]; errors: any[] }> {
  return apiFetch('/leads/bulk-run', {
    method: 'POST',
    body: JSON.stringify(leadIds),
  });
}

export async function getDrafts(leadId: string): Promise<{ items: any[] }> {
  return apiFetch<{ items: any[] }>(`/leads/${leadId}/drafts`);
}

export async function approveDraft(leadId: string, draftId: string): Promise<any> {
  return apiFetch<any>(`/leads/${leadId}/drafts/${draftId}/approve_send`, {
    method: 'POST',
  });
}

export async function submitFeedback(leadId: string, data: {
  outcome: string;
  notes?: string;
}): Promise<Feedback> {
  return apiFetch<Feedback>(`/leads/${leadId}/feedback`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getActivity(leadId: string): Promise<{ items: ActivityLog[] }> {
  return apiFetch<{ items: ActivityLog[] }>(`/leads/${leadId}/activity`);
}

export async function getScoringConfig(): Promise<ScoringConfig> {
  return apiFetch<ScoringConfig>('/settings/scoring-config');
}

export async function updateScoringConfig(config: {
  weights?: Record<string, number>;
  thresholds?: Record<string, number>;
}): Promise<ScoringConfig> {
  return apiFetch<ScoringConfig>('/settings/scoring-config', {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

export async function getOutcomeStages(leadId: string): Promise<{ items: OutcomeStageRecord[] }> {
  return apiFetch<{ items: OutcomeStageRecord[] }>(`/leads/${leadId}/outcome-stages`);
}

export async function getNextStages(leadId: string): Promise<NextStagesResponse> {
  return apiFetch<NextStagesResponse>(`/leads/${leadId}/next-stages`);
}

export async function transitionOutcomeStage(leadId: string, data: {
  stage: string;
  notes?: string;
}): Promise<OutcomeStageRecord> {
  return apiFetch<OutcomeStageRecord>(`/leads/${leadId}/outcome-stages`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function simulateReply(leadId: string, data: { reply_body: string }): Promise<InboundReplyResponse> {
  return apiFetch<InboundReplyResponse>(`/leads/${leadId}/inbound-reply`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getClassifications(leadId: string): Promise<{ items: ReplyClassification[] }> {
  return apiFetch<{ items: ReplyClassification[] }>(`/leads/${leadId}/classifications`);
}

export async function overrideClassification(
  leadId: string,
  classificationId: string,
  data: { new_classification: string; notes?: string }
): Promise<ReplyClassification> {
  return apiFetch<ReplyClassification>(`/leads/${leadId}/classifications/${classificationId}/override`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getNotifications(unreadOnly?: boolean): Promise<{ items: Notification[] }> {
  const params = unreadOnly ? '?unread_only=true' : '';
  return apiFetch<{ items: Notification[] }>(`/notifications${params}`);
}

export async function markNotificationRead(id: string): Promise<Notification> {
  return apiFetch<Notification>(`/notifications/${id}/read`, {
    method: 'POST',
  });
}

export async function markAllNotificationsRead(): Promise<{ marked_read: number }> {
  return apiFetch<{ marked_read: number }>('/notifications/read-all', {
    method: 'POST',
  });
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiFetch<DashboardStats>('/dashboard/stats');
}
