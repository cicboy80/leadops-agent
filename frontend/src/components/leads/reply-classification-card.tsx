'use client';

import { useState } from 'react';
import { Bot, AlertCircle, Calendar, ArrowRight, Edit3 } from 'lucide-react';
import { overrideClassification } from '@/lib/api';
import type { ReplyClassificationType } from '@/lib/types';

interface ReplyClassificationCardProps {
  leadId: string;
  classificationId?: string;
  classification: ReplyClassificationType;
  confidence: number;
  reasoning: string;
  extractedDates?: string[];
  autoActionTaken?: string | null;
  isAutoReply?: boolean;
  overriddenClassification?: string | null;
  onOverride?: () => void;
}

const CLASSIFICATION_CONFIG: Record<string, { label: string; color: string; description: string }> = {
  INTERESTED_BOOK_DEMO: {
    label: 'Interested - Book Demo',
    color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    description: 'Lead wants to schedule a demo or meeting',
  },
  NOT_INTERESTED: {
    label: 'Not Interested',
    color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    description: 'Lead declined or expressed disinterest',
  },
  QUESTION: {
    label: 'Question',
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    description: 'Lead asking questions, needs follow-up',
  },
  OUT_OF_OFFICE: {
    label: 'Out of Office',
    color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    description: 'Auto-reply / out of office detected',
  },
  UNSUBSCRIBE: {
    label: 'Unsubscribe',
    color: 'bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-400',
    description: 'Lead wants to stop receiving emails',
  },
  UNCLEAR: {
    label: 'Unclear',
    color: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
    description: 'Reply needs human review',
  },
};

const OVERRIDE_OPTIONS: ReplyClassificationType[] = [
  'INTERESTED_BOOK_DEMO',
  'NOT_INTERESTED',
  'QUESTION',
  'OUT_OF_OFFICE',
  'UNSUBSCRIBE',
  'UNCLEAR',
];

export function ReplyClassificationCard({
  leadId,
  classificationId,
  classification,
  confidence,
  reasoning,
  extractedDates,
  autoActionTaken,
  isAutoReply,
  overriddenClassification,
  onOverride,
}: ReplyClassificationCardProps) {
  const [showOverride, setShowOverride] = useState(false);
  const [selectedOverride, setSelectedOverride] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const effectiveClassification = overriddenClassification || classification;
  const config = CLASSIFICATION_CONFIG[effectiveClassification] || CLASSIFICATION_CONFIG.UNCLEAR;
  const confidencePercent = Math.round(confidence * 100);

  const handleOverride = async () => {
    if (!selectedOverride || !classificationId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await overrideClassification(leadId, classificationId, {
        new_classification: selectedOverride,
      });
      setShowOverride(false);
      setSelectedOverride('');
      if (onOverride) onOverride();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to override');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Bot className="w-4 h-4 text-indigo-500" />
        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Agent Classification
        </span>
        {isAutoReply && (
          <span className="text-xs bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 px-2 py-0.5 rounded">
            Auto-reply
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${config.color}`}>
          {config.label}
        </span>
        {overriddenClassification && (
          <span className="text-xs text-slate-500 dark:text-slate-400">
            (overridden from {CLASSIFICATION_CONFIG[classification]?.label || classification})
          </span>
        )}
      </div>

      {/* Confidence bar */}
      <div>
        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
          <span>Confidence</span>
          <span>{confidencePercent}%</span>
        </div>
        <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              confidencePercent >= 80
                ? 'bg-green-500'
                : confidencePercent >= 60
                ? 'bg-yellow-500'
                : 'bg-red-500'
            }`}
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
      </div>

      {/* Reasoning */}
      <p className="text-sm text-slate-600 dark:text-slate-400">{reasoning}</p>

      {/* Extracted dates */}
      {extractedDates && extractedDates.length > 0 && (
        <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
          <Calendar className="w-4 h-4" />
          <span>Dates mentioned: {extractedDates.join(', ')}</span>
        </div>
      )}

      {/* Auto action */}
      {autoActionTaken && (
        <div className="flex items-center gap-2 p-2 bg-indigo-50 dark:bg-indigo-900/20 rounded text-sm text-indigo-700 dark:text-indigo-400">
          <ArrowRight className="w-4 h-4 flex-shrink-0" />
          {autoActionTaken}
        </div>
      )}

      {/* Override section */}
      {classificationId && !overriddenClassification && (
        <>
          {!showOverride ? (
            <button
              onClick={() => setShowOverride(true)}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
            >
              <Edit3 className="w-3 h-3" />
              Override classification
            </button>
          ) : (
            <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-700">
              <select
                value={selectedOverride}
                onChange={(e) => setSelectedOverride(e.target.value)}
                className="input w-full text-sm"
                disabled={isSubmitting}
              >
                <option value="">Select correct classification...</option>
                {OVERRIDE_OPTIONS.filter((o) => o !== classification).map((opt) => (
                  <option key={opt} value={opt}>
                    {CLASSIFICATION_CONFIG[opt]?.label || opt}
                  </option>
                ))}
              </select>
              <div className="flex gap-2">
                <button
                  onClick={handleOverride}
                  disabled={isSubmitting || !selectedOverride}
                  className="btn-primary text-xs"
                >
                  {isSubmitting ? 'Saving...' : 'Confirm Override'}
                </button>
                <button
                  onClick={() => { setShowOverride(false); setSelectedOverride(''); }}
                  className="btn-secondary text-xs"
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
              </div>
              {error && (
                <div className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
                  <AlertCircle className="w-3 h-3" />
                  {error}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
