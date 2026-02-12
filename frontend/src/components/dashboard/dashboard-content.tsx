'use client';

import { useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { Activity } from 'lucide-react';
import { KpiCards } from './kpi-cards';
import { ProcessLeadsButton } from './process-leads-button';
import { LeadsTable } from '@/components/leads/leads-table';
import { getLeads, getDashboardStats } from '@/lib/api';
import type { DashboardStats, Lead } from '@/lib/types';

interface DashboardContentProps {
  initialStats: DashboardStats;
  initialLeads: Lead[];
  heading: string;
  hasFilter: boolean;
  leadParams: { limit: number; score_label?: string; status?: string; outcome_stage?: string };
}

export function DashboardContent({
  initialStats,
  initialLeads,
  heading,
  hasFilter,
  leadParams,
}: DashboardContentProps) {
  const [stats, setStats] = useState(initialStats);
  const [leads, setLeads] = useState(initialLeads);

  const refreshData = useCallback(async () => {
    try {
      const [newStats, leadsResponse] = await Promise.all([
        getDashboardStats(),
        getLeads(leadParams),
      ]);
      setStats(newStats);
      setLeads(leadsResponse.items);
    } catch (error) {
      console.error('Failed to refresh dashboard data:', error);
    }
  }, [leadParams]);

  // Always refetch on mount — ensures fresh data even when Next.js serves
  // a cached RSC payload after client-side navigation (e.g. returning from
  // a lead detail page where the user approved an email or booked a demo).
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Also refetch when the browser tab regains focus
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') refreshData();
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [refreshData]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
          Dashboard
        </h1>
        <p className="text-slate-600 dark:text-slate-400">
          Overview of your lead pipeline performance
        </p>
      </div>

      <KpiCards stats={stats} />

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Activity className="w-5 h-5" />
              {heading}
            </h2>
            {hasFilter && (
              <Link
                href="/"
                className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                Show All
              </Link>
            )}
          </div>
          <div className="flex items-center gap-3">
            <ProcessLeadsButton onProcessingComplete={refreshData} />
            <a href="/upload" className="btn-primary">
              Upload New Leads
            </a>
          </div>
        </div>

        <LeadsTable leads={leads} />
      </div>
    </div>
  );
}
