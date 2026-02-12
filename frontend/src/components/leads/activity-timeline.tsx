import { Clock, Reply } from 'lucide-react';
import type { ActivityLog } from '@/lib/types';

interface ActivityTimelineProps {
  activities: ActivityLog[];
}

export function ActivityTimeline({ activities }: ActivityTimelineProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(date);
  };

  const getEventIcon = (eventType: string) => {
    if (eventType === 'EMAIL_REPLIED') return <Reply className="w-4 h-4" />;
    return <Clock className="w-4 h-4" />;
  };

  const getEventColor = (eventType: string) => {
    const colors: Record<string, string> = {
      lead_created: 'bg-blue-500',
      lead_scored: 'bg-purple-500',
      decision_made: 'bg-indigo-500',
      email_drafted: 'bg-green-500',
      email_approved: 'bg-emerald-500',
      email_sent: 'bg-teal-500',
      EMAIL_REPLIED: 'bg-cyan-500',
      feedback_submitted: 'bg-amber-500',
    };
    return colors[eventType] || 'bg-slate-500';
  };

  if (activities.length === 0) {
    return (
      <div className="text-center py-8">
        <Clock className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">No activity yet</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Run the pipeline to start scoring and generating emails
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {activities.map((activity, index) => (
        <div key={activity.id} className="flex gap-4">
          <div className="flex flex-col items-center">
            <div className={`w-8 h-8 rounded-full ${getEventColor(activity.type)} flex items-center justify-center text-white`}>
              {getEventIcon(activity.type)}
            </div>
            {index < activities.length - 1 && (
              <div className="w-0.5 flex-1 bg-slate-200 dark:bg-slate-700 mt-2" style={{ minHeight: '20px' }} />
            )}
          </div>

          <div className="flex-1 pb-6">
            <div className="flex items-center justify-between mb-1">
              <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100">
                {activity.type.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
              </h4>
              <time className="text-xs text-slate-500 dark:text-slate-400">
                {formatDate(activity.created_at)}
              </time>
            </div>

            {activity.type === 'EMAIL_REPLIED' && activity.payload?.reply_body && (
              <div className="mt-2 p-2 bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800 rounded text-xs text-cyan-800 dark:text-cyan-300">
                <p className="font-medium mb-1">Reply received{activity.payload.sender_email ? ` from ${activity.payload.sender_email}` : ''}:</p>
                <p className="whitespace-pre-wrap">{activity.payload.reply_body}</p>
              </div>
            )}

            {activity.type !== 'EMAIL_REPLIED' && activity.payload && Object.keys(activity.payload).length > 0 && (
              <div className="mt-2 p-2 bg-slate-50 dark:bg-slate-800 rounded text-xs">
                <pre className="text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
                  {JSON.stringify(activity.payload, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
