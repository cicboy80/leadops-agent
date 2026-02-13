'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, AlertCircle, ArrowRight, ChevronDown } from 'lucide-react';
import { getNextStages, transitionOutcomeStage, getClassifications } from '@/lib/api';
import { ReplyClassificationCard } from '@/components/leads/reply-classification-card';
import type { ReplyClassification } from '@/lib/types';

interface FeedbackFormProps {
  leadId: string;
  currentStage?: string | null;
  onSuccess?: () => void;
}

const STAGE_LABELS: Record<string, string> = {
  EMAIL_SENT: 'Email Sent',
  RESPONDED: 'Responded',
  NO_RESPONSE: 'No Response',
  BOOKED_DEMO: 'Booked Demo',
  CLOSED_WON: 'Closed Won',
  CLOSED_LOST: 'Closed Lost',
  DISQUALIFIED: 'Disqualified',
};

const AUTOMATED_TRANSITIONS: Record<string, Set<string>> = {
  EMAIL_SENT: new Set(['RESPONDED', 'NO_RESPONSE']),
  NO_RESPONSE: new Set(['RESPONDED']),
  CLOSED_LOST: new Set(['RESPONDED']),
  DISQUALIFIED: new Set(['RESPONDED']),
};

const STAGE_COLORS: Record<string, string> = {
  EMAIL_SENT: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  RESPONDED: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  NO_RESPONSE: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  BOOKED_DEMO: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  CLOSED_WON: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  CLOSED_LOST: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  DISQUALIFIED: 'bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-400',
};

export function FeedbackForm({ leadId, currentStage, onSuccess }: FeedbackFormProps) {
  const [selectedStage, setSelectedStage] = useState('');
  const [notes, setNotes] = useState('');
  const [nextStages, setNextStages] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [latestClassification, setLatestClassification] = useState<ReplyClassification | null>(null);
  const [showManualOverride, setShowManualOverride] = useState(false);

  useEffect(() => {
    loadNextStages();
    loadLatestClassification();
  }, [leadId, currentStage]);

  const loadNextStages = async () => {
    setIsLoading(true);
    try {
      const data = await getNextStages(leadId);
      setNextStages(data.next_stages);
    } catch {
      setNextStages([]);
    } finally {
      setIsLoading(false);
    }
  };

  const loadLatestClassification = async () => {
    try {
      const data = await getClassifications(leadId);
      if (data.items && data.items.length > 0) {
        setLatestClassification(data.items[0]);
      } else {
        setLatestClassification(null);
      }
    } catch {
      setLatestClassification(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedStage) {
      setError('Please select a stage');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setSuccess(false);

    try {
      await transitionOutcomeStage(leadId, {
        stage: selectedStage,
        notes: notes || undefined,
      });

      setSuccess(true);
      setSelectedStage('');
      setNotes('');

      if (onSuccess) {
        onSuccess();
      }

      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update stage');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!currentStage) {
    return (
      <div className="text-sm text-slate-500 dark:text-slate-400">
        No outcome stage yet. Approve and send an email to start tracking.
      </div>
    );
  }

  const handleRefresh = () => {
    loadLatestClassification();
    loadNextStages();
    if (onSuccess) onSuccess();
  };

  return (
    <div className="space-y-4">
      <div>
        <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Current Stage</div>
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${STAGE_COLORS[currentStage] || 'bg-slate-100 text-slate-800'}`}>
          {STAGE_LABELS[currentStage] || currentStage}
        </span>
      </div>

      {/* Show latest classification if available */}
      {latestClassification && (
        <ReplyClassificationCard
          leadId={leadId}
          classificationId={latestClassification.id}
          classification={latestClassification.classification}
          confidence={latestClassification.confidence}
          reasoning={latestClassification.reasoning}
          extractedDates={latestClassification.extracted_dates || undefined}
          isAutoReply={latestClassification.is_auto_reply}
          overriddenClassification={latestClassification.overridden_classification}
          onOverride={handleRefresh}
        />
      )}

      {(() => {
        const manualStages = nextStages.filter(
          (stage) => !AUTOMATED_TRANSITIONS[currentStage]?.has(stage)
        );

        if (isLoading) {
          return <div className="text-sm text-slate-500">Loading transitions...</div>;
        }

        if (nextStages.length === 0) {
          return (
            <div className="text-sm text-slate-500 dark:text-slate-400">
              This is a terminal stage. No further transitions available.
            </div>
          );
        }

        if (manualStages.length === 0 && !latestClassification) {
          return (
            <div className="text-sm text-slate-500 dark:text-slate-400">
              Stage will update automatically when the lead responds.
            </div>
          );
        }

        if (manualStages.length === 0) {
          return null;
        }

        // If classification exists, show manual override as collapsible
        if (latestClassification && !showManualOverride) {
          return (
            <div className="space-y-1">
              <p className="text-xs text-amber-700 dark:text-amber-300">
                Use manual override to close the deal (Won/Lost).
              </p>
              <button
                onClick={() => setShowManualOverride(true)}
                className="flex items-center gap-1 text-sm font-medium text-amber-600 hover:text-amber-800 dark:text-amber-400 dark:hover:text-amber-200"
              >
                <ChevronDown className="w-4 h-4" />
                Manual stage override
              </button>
            </div>
          );
        }

        return (
          <form onSubmit={handleSubmit} className="space-y-4">
            {latestClassification && (
              <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                Manual Override
              </div>
            )}
            <div>
              <label htmlFor="stage" className="label mb-2 block">
                Transition To
              </label>
              <select
                id="stage"
                value={selectedStage}
                onChange={(e) => setSelectedStage(e.target.value)}
                className="input w-full"
                disabled={isSubmitting}
              >
                <option value="">Select next stage...</option>
                {manualStages.map((stage) => (
                  <option key={stage} value={stage}>
                    {STAGE_LABELS[stage] || stage}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="notes" className="label mb-2 block">
                Notes (optional)
              </label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any additional context..."
                className="textarea w-full"
                rows={3}
                disabled={isSubmitting}
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-800 dark:text-red-400">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {success && (
              <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-sm text-green-800 dark:text-green-400">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                Stage updated successfully
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || !selectedStage}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                'Updating...'
              ) : (
                <>
                  <ArrowRight className="w-4 h-4" />
                  Update Stage
                </>
              )}
            </button>
          </form>
        );
      })()}
    </div>
  );
}
