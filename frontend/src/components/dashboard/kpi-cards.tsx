import Link from 'next/link';
import {
  Users,
  Flame,
  ThermometerSun,
  Snowflake,
  Mail,
  Calendar
} from 'lucide-react';
import type { DashboardStats } from '@/lib/types';

interface KpiCardsProps {
  stats: DashboardStats;
}

export function KpiCards({ stats }: KpiCardsProps) {
  const cards = [
    {
      title: 'Total Leads',
      value: stats.total_leads,
      icon: Users,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-100 dark:bg-blue-900/20',
      href: '/',
    },
    {
      title: 'Hot Leads',
      value: stats.hot_leads,
      icon: Flame,
      color: 'text-red-600 dark:text-red-400',
      bgColor: 'bg-red-100 dark:bg-red-900/20',
      href: '/?score_label=HOT',
    },
    {
      title: 'Warm Leads',
      value: stats.warm_leads,
      icon: ThermometerSun,
      color: 'text-amber-600 dark:text-amber-400',
      bgColor: 'bg-amber-100 dark:bg-amber-900/20',
      href: '/?score_label=WARM',
    },
    {
      title: 'Cold Leads',
      value: stats.cold_leads,
      icon: Snowflake,
      color: 'text-sky-600 dark:text-sky-400',
      bgColor: 'bg-sky-100 dark:bg-sky-900/20',
      href: '/?score_label=COLD',
    },
    {
      title: 'Contacted',
      value: stats.contacted,
      icon: Mail,
      color: 'text-purple-600 dark:text-purple-400',
      bgColor: 'bg-purple-100 dark:bg-purple-900/20',
      href: '/?outcome_stage=EMAIL_SENT',
    },
    {
      title: 'Meetings Booked',
      value: stats.meetings_booked,
      icon: Calendar,
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-100 dark:bg-green-900/20',
      href: '/?outcome_stage=BOOKED_DEMO',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <Link key={card.title} href={card.href} className="card p-6 hover:ring-2 hover:ring-blue-400 transition-all cursor-pointer">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
                  {card.title}
                </p>
                <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                  {card.value}
                </p>
              </div>
              <div className={`${card.bgColor} ${card.color} p-3 rounded-lg`}>
                <Icon className="w-6 h-6" />
              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
