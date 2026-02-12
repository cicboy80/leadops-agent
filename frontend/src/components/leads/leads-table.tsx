'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowUpDown, ExternalLink, Upload } from 'lucide-react';
import { ScoreBadge } from './score-badge';
import type { Lead } from '@/lib/types';
import clsx from 'clsx';

interface LeadsTableProps {
  leads: Lead[];
}

type SortField = 'score' | 'created_at' | 'company' | 'name';
type SortDirection = 'asc' | 'desc';

export function LeadsTable({ leads }: LeadsTableProps) {
  const [sortField, setSortField] = useState<SortField>('score');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedLeads = [...leads].sort((a, b) => {
    let aVal: any;
    let bVal: any;

    switch (sortField) {
      case 'score':
        aVal = a.score_value || 0;
        bVal = b.score_value || 0;
        break;
      case 'created_at':
        aVal = new Date(a.created_at || 0).getTime();
        bVal = new Date(b.created_at || 0).getTime();
        break;
      case 'company':
        aVal = a.company_name || '';
        bVal = b.company_name || '';
        break;
      case 'name':
        aVal = `${a.first_name || ''} ${a.last_name || ''}`;
        bVal = `${b.first_name || ''} ${b.last_name || ''}`;
        break;
    }

    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  const getStatusBadge = (status?: string | null) => {
    const statusStyles: Record<string, string> = {
      NEW: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
      QUALIFIED: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
      NEEDS_INFO: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
      DISQUALIFIED: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
      CONTACTED: 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
      MEETING_BOOKED: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-400',
      CLOSED_WON: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
      CLOSED_LOST: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
    };

    return (
      <span className={clsx(
        'inline-flex px-2 py-1 rounded-full text-xs font-medium',
        statusStyles[status || 'NEW'] || statusStyles.NEW
      )}>
        {(status || 'NEW').replace('_', ' ')}
      </span>
    );
  };

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-50 dark:bg-slate-800 border-b">
            <tr>
              <th className="px-6 py-3 text-left">
                <button
                  onClick={() => handleSort('name')}
                  className="flex items-center gap-1 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white"
                >
                  Name
                  <ArrowUpDown className="w-3 h-3" />
                </button>
              </th>
              <th className="px-6 py-3 text-left">
                <button
                  onClick={() => handleSort('company')}
                  className="flex items-center gap-1 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white"
                >
                  Company
                  <ArrowUpDown className="w-3 h-3" />
                </button>
              </th>
              <th className="px-6 py-3 text-left">
                <button
                  onClick={() => handleSort('score')}
                  className="flex items-center gap-1 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white"
                >
                  Score
                  <ArrowUpDown className="w-3 h-3" />
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-300">
                Status
              </th>
              <th className="px-6 py-3 text-left">
                <button
                  onClick={() => handleSort('created_at')}
                  className="flex items-center gap-1 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white"
                >
                  Date
                  <ArrowUpDown className="w-3 h-3" />
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-300">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {sortedLeads.map((lead) => (
              <tr key={lead.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                <td className="px-6 py-4">
                  <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {lead.first_name} {lead.last_name}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {lead.email}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-slate-900 dark:text-slate-100">
                    {lead.company_name || '-'}
                  </div>
                  {lead.job_title && (
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {lead.job_title}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4">
                  {lead.score_value !== null && lead.score_value !== undefined ? (
                    <ScoreBadge score={lead.score_value} tier={lead.score_label} />
                  ) : (
                    <span className="text-sm text-slate-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  {getStatusBadge(lead.status)}
                </td>
                <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-400">
                  {lead.created_at
                    ? new Date(lead.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })
                    : '-'}
                </td>
                <td className="px-6 py-4">
                  <Link
                    href={`/leads/${lead.id}`}
                    className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    View
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {sortedLeads.length === 0 && (
        <div className="px-6 py-16 text-center">
          <Upload className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">No leads yet</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 mb-4">Upload a CSV to get started</p>
          <Link
            href="/upload"
            className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
          >
            <Upload className="w-4 h-4" />
            Go to Upload
          </Link>
        </div>
      )}
    </div>
  );
}
