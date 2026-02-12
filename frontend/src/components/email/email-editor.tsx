'use client';

import { useState } from 'react';
import { Send, CheckCircle2, XCircle, AlertCircle, Reply } from 'lucide-react';
import { approveDraft, simulateReply } from '@/lib/api';
import { revalidateDashboard } from '@/app/actions';
import { ReplyClassificationCard } from '@/components/leads/reply-classification-card';
import type { EmailDraft } from '@/lib/types';
import type { InboundReplyResponse } from '@/lib/types';

interface EmailEditorProps {
  draft: EmailDraft;
  onApprove?: () => void;
  onReject?: () => void;
}

export function EmailEditor({ draft, onApprove, onReject }: EmailEditorProps) {
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showReplyForm, setShowReplyForm] = useState(false);
  const [replyText, setReplyText] = useState('');
  const [isSimulating, setIsSimulating] = useState(false);
  const [classificationResult, setClassificationResult] = useState<InboundReplyResponse | null>(null);

  const handleApprove = async () => {
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      await approveDraft(draft.lead_id, draft.id);
      setSuccess('Email approved and queued for sending');
      await revalidateDashboard();
      if (onApprove) {
        onApprove();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve email');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isEditable = !draft.approved;

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="subject" className="label mb-2 block">
          Subject
        </label>
        <input
          id="subject"
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="input w-full"
          disabled={!isEditable || isSubmitting}
        />
      </div>

      <div>
        <label htmlFor="body" className="label mb-2 block">
          Email Body
        </label>
        <textarea
          id="body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          className="textarea w-full"
          rows={12}
          disabled={!isEditable || isSubmitting}
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
          {success}
        </div>
      )}

      {!draft.approved && (
        <div className="flex gap-3">
          <button
            onClick={handleApprove}
            disabled={isSubmitting}
            className="btn-primary flex-1 flex items-center justify-center gap-2"
          >
            <Send className="w-4 h-4" />
            {isSubmitting ? 'Processing...' : 'Approve & Send'}
          </button>
        </div>
      )}

      {draft.approved && (
        <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-sm text-green-800 dark:text-green-400">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          Email approved
        </div>
      )}

      {draft.sent_at && (
        <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-sm text-blue-800 dark:text-blue-400">
          <Send className="w-4 h-4 flex-shrink-0" />
          Email sent on {new Date(draft.sent_at).toLocaleString()}
        </div>
      )}

      {/* Classification result after simulate reply */}
      {classificationResult && (
        <ReplyClassificationCard
          leadId={draft.lead_id}
          classification={classificationResult.classification}
          confidence={classificationResult.confidence}
          reasoning={classificationResult.reasoning}
          extractedDates={classificationResult.extracted_dates}
          autoActionTaken={classificationResult.auto_action_taken}
          onOverride={() => {
            setClassificationResult(null);
            if (onApprove) onApprove();
          }}
        />
      )}

      {draft.sent_at && draft.delivery_status === 'SENT' && (
        <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-4">
          {!showReplyForm ? (
            <button
              onClick={() => setShowReplyForm(true)}
              className="flex items-center gap-2 text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
            >
              <Reply className="w-4 h-4" />
              Simulate Reply
            </button>
          ) : (
            <div className="space-y-3">
              <label htmlFor="reply-text" className="label mb-1 block text-sm">
                Reply Text
              </label>
              <textarea
                id="reply-text"
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                className="textarea w-full"
                rows={4}
                placeholder="Simulate what the lead replied with..."
                disabled={isSimulating}
              />
              <div className="flex gap-2">
                <button
                  onClick={async () => {
                    if (!replyText.trim()) return;
                    setIsSimulating(true);
                    setError(null);
                    setClassificationResult(null);
                    try {
                      const result = await simulateReply(draft.lead_id, { reply_body: replyText });
                      setClassificationResult(result);
                      setShowReplyForm(false);
                      setReplyText('');
                      await revalidateDashboard();
                      if (onApprove) onApprove();
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Failed to simulate reply');
                    } finally {
                      setIsSimulating(false);
                    }
                  }}
                  disabled={isSimulating || !replyText.trim()}
                  className="btn-primary flex items-center gap-2 text-sm"
                >
                  <Reply className="w-4 h-4" />
                  {isSimulating ? 'Sending...' : 'Send Reply'}
                </button>
                <button
                  onClick={() => { setShowReplyForm(false); setReplyText(''); }}
                  className="btn-secondary text-sm"
                  disabled={isSimulating}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
