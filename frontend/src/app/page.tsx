import { DashboardContent } from '@/components/dashboard/dashboard-content';
import { getLeads, getDashboardStats } from '@/lib/api';
import type { DashboardStats, Lead } from '@/lib/types';

export const dynamic = 'force-dynamic';

const FILTER_LABELS: Record<string, string> = {
  'score_label=HOT': 'Hot Leads',
  'score_label=WARM': 'Warm Leads',
  'score_label=COLD': 'Cold Leads',
  'outcome_stage=EMAIL_SENT': 'Contacted Leads',
  'outcome_stage=BOOKED_DEMO': 'Meetings Booked',
};

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function DashboardPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const scoreLabel = typeof params.score_label === 'string' ? params.score_label : undefined;
  const status = typeof params.status === 'string' ? params.status : undefined;
  const outcomeStage = typeof params.outcome_stage === 'string' ? params.outcome_stage : undefined;

  const hasFilter = !!(scoreLabel || status || outcomeStage);

  const leadParams: { limit: number; score_label?: string; status?: string; outcome_stage?: string } = { limit: 50 };
  if (scoreLabel) {
    leadParams.score_label = scoreLabel;
    leadParams.status = 'NEW';
  } else if (outcomeStage) {
    leadParams.outcome_stage = outcomeStage;
  } else if (status) {
    leadParams.status = status;
  } else {
    leadParams.status = 'NEW';
  }

  let filterKey = '';
  if (scoreLabel) filterKey = `score_label=${scoreLabel}`;
  else if (outcomeStage) filterKey = `outcome_stage=${outcomeStage}`;
  else if (status) filterKey = `status=${status}`;
  const heading = FILTER_LABELS[filterKey] || 'Recent Leads';

  let stats: DashboardStats;
  let leads: Lead[];
  try {
    const [statsResult, leadsResponse] = await Promise.all([
      getDashboardStats(),
      getLeads(leadParams),
    ]);
    stats = statsResult;
    leads = leadsResponse.items;
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error);
    stats = {
      total_leads: 0,
      hot_leads: 0,
      warm_leads: 0,
      cold_leads: 0,
      contacted: 0,
      meetings_booked: 0,
      responded: 0,
      closed_won: 0,
      closed_lost: 0,
    };
    leads = [];
  }

  return (
    <DashboardContent
      initialStats={stats}
      initialLeads={leads}
      heading={heading}
      hasFilter={hasFilter}
      leadParams={leadParams}
    />
  );
}
