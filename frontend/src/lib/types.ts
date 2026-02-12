export interface Lead {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  company_name: string;
  phone?: string | null;
  job_title?: string | null;
  industry?: string | null;
  company_size?: string | null;
  country?: string | null;
  source?: string | null;
  budget_range?: string | null;
  pain_point?: string | null;
  urgency?: string | null;
  lead_message?: string | null;

  status: 'NEW' | 'QUALIFIED' | 'NEEDS_INFO' | 'DISQUALIFIED' | 'CONTACTED' | 'MEETING_BOOKED' | 'CLOSED_WON' | 'CLOSED_LOST';
  score_label?: 'HOT' | 'WARM' | 'COLD' | null;
  score_value?: number | null;
  score_rationale?: string | null;
  recommended_action?: 'SEND_EMAIL' | 'ASK_QUESTION' | 'DISQUALIFY' | 'HOLD' | null;

  enrichment_data?: Record<string, any> | null;
  score_breakdown?: Array<{ factor: string; points: number; max: number }> | null;
  processing_status: string;

  current_outcome_stage?: string | null;
  outcome_stage_entered_at?: string | null;

  created_at: string;
  updated_at: string;
  archived_at?: string | null;
}

export interface LeadListResponse {
  items: Lead[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface EmailDraft {
  id: string;
  lead_id: string;
  subject: string;
  body: string;
  variant: string;
  approved: boolean;
  sent_at?: string | null;
  delivery_status: string;
  created_at: string;
}

export interface ActivityLog {
  id: string;
  lead_id: string;
  type: string;
  payload?: Record<string, any> | null;
  created_at: string;
}

export interface Feedback {
  id: string;
  lead_id: string;
  outcome: string;
  notes?: string | null;
  created_at: string;
}

export interface Trace {
  id: string;
  lead_id: string;
  graph_run_id: string;
  node_events?: Record<string, any> | null;
  llm_inputs?: Record<string, any> | null;
  llm_outputs?: Record<string, any> | null;
  created_at: string;
}

export interface ScoringConfig {
  id: string;
  weights: Record<string, number>;
  thresholds: Record<string, number>;
  updated_at: string;
  updated_by?: string | null;
}

export interface HealthResponse {
  status: string;
  database: string;
  llm: string;
  version: string;
}

export interface UploadResponse {
  created: number;
  errors: Array<Record<string, any>>;
}

export interface PipelineRunResponse {
  id: string;
  lead_id: string;
  thread_id: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  node_timings?: Record<string, any> | null;
}

export interface OutcomeStageRecord {
  id: string;
  lead_id: string;
  stage: string;
  previous_stage?: string | null;
  reason: string;
  triggered_by?: string | null;
  notes?: string | null;
  metadata_json?: Record<string, any> | null;
  entered_at: string;
  exited_at?: string | null;
}

export interface NextStagesResponse {
  current_stage: string | null;
  next_stages: string[];
}

export interface DashboardStats {
  total_leads: number;
  hot_leads: number;
  warm_leads: number;
  cold_leads: number;
  contacted: number;
  meetings_booked: number;
  responded: number;
  closed_won: number;
  closed_lost: number;
}

export type ReplyClassificationType =
  | 'INTERESTED_BOOK_DEMO'
  | 'NOT_INTERESTED'
  | 'QUESTION'
  | 'OUT_OF_OFFICE'
  | 'UNSUBSCRIBE'
  | 'UNCLEAR';

export interface ReplyClassification {
  id: string;
  lead_id: string;
  reply_body: string;
  classification: ReplyClassificationType;
  confidence: number;
  reasoning: string;
  extracted_dates?: string[] | null;
  is_auto_reply: boolean;
  overridden_by?: string | null;
  overridden_classification?: string | null;
  overridden_at?: string | null;
  created_at: string;
}

export interface InboundReplyResponse {
  stage_record: OutcomeStageRecord | null;
  classification: ReplyClassificationType;
  confidence: number;
  reasoning: string;
  extracted_dates: string[];
  auto_action_taken: string | null;
}

export interface Notification {
  id: string;
  lead_id: string | null;
  type: string;
  title: string;
  body: string;
  metadata_json?: Record<string, any> | null;
  read_at: string | null;
  created_at: string;
}
