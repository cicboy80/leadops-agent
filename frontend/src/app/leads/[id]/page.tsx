'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Mail,
  Building2,
  Briefcase,
  MapPin,
  User,
  AlertCircle,
  Play,
  Loader2,
  BarChart3,
  Send,
  Reply,
  CalendarCheck,
  Trophy,
  FileText,
} from 'lucide-react';
import { ScoreBadge } from '@/components/leads/score-badge';
import { ActivityTimeline } from '@/components/leads/activity-timeline';
import { FeedbackForm } from '@/components/leads/feedback-form';
import { EmailEditor } from '@/components/email/email-editor';
import { ReplyClassificationCard } from '@/components/leads/reply-classification-card';
import { getLead, getDrafts, getActivity, getOutcomeStages, getClassifications, runPipeline, transitionOutcomeStage } from '@/lib/api';
import type { Lead, EmailDraft, ActivityLog, OutcomeStageRecord, ReplyClassification } from '@/lib/types';

const STAGE_LABELS: Record<string, string> = {
  EMAIL_SENT: 'Email Sent',
  RESPONDED: 'Responded',
  NO_RESPONSE: 'No Response',
  BOOKED_DEMO: 'Booked Demo',
  CLOSED_WON: 'Closed Won',
  CLOSED_LOST: 'Closed Lost',
  DISQUALIFIED: 'Disqualified',
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

const VARIANT_LABELS: Record<string, string> = {
  FIRST_TOUCH: 'First Touch',
  first_touch: 'First Touch',
  FOLLOW_UP_1: 'Follow-up #1',
  follow_up_1: 'Follow-up #1',
  FOLLOW_UP_2: 'Follow-up #2',
  follow_up_2: 'Follow-up #2',
  BREAKUP: 'Breakup',
  breakup: 'Breakup',
  QUESTION_RESPONSE: 'Question Response',
  question_response: 'Question Response',
  DEMO_CONFIRMATION: 'Demo Confirmation',
  demo_confirmation: 'Demo Confirmation',
  NURTURE: 'Nurture',
  nurture: 'Nurture',
  RE_ENGAGEMENT: 'Re-engagement',
  re_engagement: 'Re-engagement',
};

function StageBadge({ stage }: { stage: string }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STAGE_COLORS[stage] || 'bg-slate-100 text-slate-800'}`}>
      {STAGE_LABELS[stage] || stage}
    </span>
  );
}

function ScoreBreakdown({ breakdown, totalScore }: { breakdown: Array<{ factor: string; points: number; max: number }>; totalScore: number }) {
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          Score Breakdown
        </h2>
        <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          {totalScore}<span className="text-sm font-normal text-slate-500">/100</span>
        </span>
      </div>
      <div className="space-y-3">
        {breakdown.map((item) => (
          <div key={item.factor}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-slate-700 dark:text-slate-300">{item.factor}</span>
              <span className="text-sm font-medium text-slate-900 dark:text-slate-100">+{item.points}</span>
            </div>
            <div className="w-full h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  item.points === 0
                    ? 'bg-slate-300 dark:bg-slate-600'
                    : item.points >= item.max * 0.8
                      ? 'bg-emerald-500'
                      : item.points >= item.max * 0.4
                        ? 'bg-amber-500'
                        : 'bg-slate-400'
                }`}
                style={{ width: `${item.max > 0 ? (item.points / item.max) * 100 : 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function QuickActions({
  lead,
  drafts,
  isRunningPipeline,
  onRunPipeline,
  onBookDemo,
}: {
  lead: Lead;
  drafts: EmailDraft[];
  isRunningPipeline: boolean;
  onRunPipeline: () => void;
  onBookDemo: () => void;
}) {
  const hasScore = lead.score_value !== null && lead.score_value !== undefined;
  const hasDraft = drafts.length > 0;
  const draftApproved = hasDraft && drafts[0].approved;
  const emailSent = hasDraft && !!drafts[0].sent_at;
  const stage = lead.current_outcome_stage;

  if (!hasScore) {
    return (
      <div className="card p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-blue-900 dark:text-blue-100">This lead hasn&apos;t been scored yet</p>
            <p className="text-xs text-blue-700 dark:text-blue-300 mt-0.5">Run the pipeline to score, decide, and draft an email</p>
          </div>
          <button
            onClick={onRunPipeline}
            disabled={isRunningPipeline}
            className="btn-primary flex items-center gap-2"
          >
            {isRunningPipeline ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Processing...</>
            ) : (
              <><Play className="w-4 h-4" /> Run Pipeline</>
            )}
          </button>
        </div>
      </div>
    );
  }

  if (stage === 'RESPONDED') {
    return (
      <div className="card p-4 bg-gradient-to-r from-purple-50 to-emerald-50 dark:from-purple-900/20 dark:to-emerald-900/20 border-purple-200 dark:border-purple-800">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-purple-900 dark:text-purple-100">Lead has responded</p>
            <p className="text-xs text-purple-700 dark:text-purple-300 mt-0.5">Move forward with a demo booking or close the deal</p>
          </div>
          <div className="flex gap-2">
            <button onClick={onBookDemo} className="btn-primary flex items-center gap-2">
              <CalendarCheck className="w-4 h-4" /> Book Demo
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (emailSent) {
    return (
      <div className="card p-4 bg-gradient-to-r from-teal-50 to-cyan-50 dark:from-teal-900/20 dark:to-cyan-900/20 border-teal-200 dark:border-teal-800">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-teal-900 dark:text-teal-100">Email sent — waiting for reply</p>
            <p className="text-xs text-teal-700 dark:text-teal-300 mt-0.5">Use &quot;Simulate Reply&quot; below to test reply classification</p>
          </div>
          <div className="flex items-center gap-2 text-teal-600 dark:text-teal-400">
            <Reply className="w-5 h-5" />
          </div>
        </div>
      </div>
    );
  }

  if (hasDraft && !draftApproved && (lead.score_label === 'HOT' || lead.score_label === 'WARM')) {
    return (
      <div className="card p-4 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-200 dark:border-green-800">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-green-900 dark:text-green-100">Email draft ready for review</p>
            <p className="text-xs text-green-700 dark:text-green-300 mt-0.5">Review the draft below and approve to send</p>
          </div>
          <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
            <Send className="w-5 h-5" />
          </div>
        </div>
      </div>
    );
  }

  if (stage === 'BOOKED_DEMO') {
    return (
      <div className="card p-4 bg-gradient-to-r from-emerald-50 to-green-50 dark:from-emerald-900/20 dark:to-green-900/20 border-emerald-200 dark:border-emerald-800">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-emerald-900 dark:text-emerald-100">Demo booked!</p>
            <p className="text-xs text-emerald-700 dark:text-emerald-300 mt-0.5">After the demo, mark this lead as Closed Won or Closed Lost</p>
          </div>
          <Trophy className="w-5 h-5 text-emerald-500" />
        </div>
      </div>
    );
  }

  return null;
}

function StageTimeline({ stages }: { stages: OutcomeStageRecord[] }) {
  return (
    <div className="relative">
      {stages.map((stage, index) => (
        <div key={stage.id} className="flex gap-3 pb-4 last:pb-0">
          <div className="flex flex-col items-center">
            <div className={`w-3 h-3 rounded-full flex-shrink-0 ${
              index === stages.length - 1
                ? 'bg-blue-500 ring-4 ring-blue-100 dark:ring-blue-900/30'
                : 'bg-slate-300 dark:bg-slate-600'
            }`} />
            {index < stages.length - 1 && (
              <div className="w-0.5 flex-1 bg-slate-200 dark:bg-slate-700 mt-1" />
            )}
          </div>
          <div className="flex-1 min-w-0 -mt-0.5">
            <div className="flex items-center gap-2">
              <StageBadge stage={stage.stage} />
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {new Date(stage.entered_at).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>
            {stage.notes && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{stage.notes}</p>
            )}
            {stage.reason === 'AUTOMATIC' && (
              <p className="text-xs text-amber-600 dark:text-amber-400 mt-0.5">Auto-transitioned</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function LeadDetailPage() {
  const params = useParams();
  const leadId = params.id as string;

  const [lead, setLead] = useState<Lead | null>(null);
  const [drafts, setDrafts] = useState<EmailDraft[]>([]);
  const [activities, setActivities] = useState<ActivityLog[]>([]);
  const [outcomeStages, setOutcomeStages] = useState<OutcomeStageRecord[]>([]);
  const [classifications, setClassifications] = useState<ReplyClassification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRunningPipeline, setIsRunningPipeline] = useState(false);

  useEffect(() => {
    loadLeadData();
  }, [leadId]);

  const loadLeadData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [leadData, draftsData, activitiesData] = await Promise.all([
        getLead(leadId),
        getDrafts(leadId),
        getActivity(leadId),
      ]);

      setLead(leadData);
      setDrafts(draftsData.items || []);
      setActivities(activitiesData.items || []);

      // Fetch outcome stages and classifications separately so they don't break the page
      try {
        const stagesData = await getOutcomeStages(leadId);
        setOutcomeStages(stagesData.items || []);
      } catch {
        setOutcomeStages([]);
      }

      try {
        const classificationsData = await getClassifications(leadId);
        setClassifications(classificationsData.items || []);
      } catch {
        setClassifications([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load lead data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunPipeline = async () => {
    setIsRunningPipeline(true);
    try {
      await runPipeline(leadId);
      await loadLeadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pipeline run failed');
    } finally {
      setIsRunningPipeline(false);
    }
  };

  const handleBookDemo = async () => {
    try {
      await transitionOutcomeStage(leadId, { stage: 'BOOKED_DEMO', notes: 'Demo booked from lead detail' });
      await loadLeadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to book demo');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-600 dark:text-slate-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-800 dark:text-red-400">
        <AlertCircle className="w-5 h-5 flex-shrink-0" />
        {error}
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-600 dark:text-slate-400">Lead not found</p>
      </div>
    );
  }

  const scoreBreakdown = lead.score_breakdown || lead.enrichment_data?.score_breakdown;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/" className="text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">
              {lead.first_name} {lead.last_name}
            </h1>
            {lead.current_outcome_stage && (
              <StageBadge stage={lead.current_outcome_stage} />
            )}
          </div>
          <p className="text-slate-600 dark:text-slate-400">{lead.email}</p>
        </div>
        {lead.score_value !== null && lead.score_value !== undefined && (
          <ScoreBadge score={lead.score_value} tier={lead.score_label} />
        )}
      </div>

      {/* Quick Actions Bar */}
      <QuickActions
        lead={lead}
        drafts={drafts}
        isRunningPipeline={isRunningPipeline}
        onRunPipeline={handleRunPipeline}
        onBookDemo={handleBookDemo}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
              Lead Profile
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {lead.company_name && (
                <div className="flex items-start gap-3">
                  <Building2 className="w-5 h-5 text-slate-400 mt-0.5" />
                  <div>
                    <div className="text-xs text-slate-600 dark:text-slate-400">Company</div>
                    <div className="text-sm font-medium text-slate-900 dark:text-slate-100">{lead.company_name}</div>
                  </div>
                </div>
              )}

              {lead.job_title && (
                <div className="flex items-start gap-3">
                  <Briefcase className="w-5 h-5 text-slate-400 mt-0.5" />
                  <div>
                    <div className="text-xs text-slate-600 dark:text-slate-400">Job Title</div>
                    <div className="text-sm font-medium text-slate-900 dark:text-slate-100">{lead.job_title}</div>
                  </div>
                </div>
              )}

              {lead.industry && (
                <div className="flex items-start gap-3">
                  <User className="w-5 h-5 text-slate-400 mt-0.5" />
                  <div>
                    <div className="text-xs text-slate-600 dark:text-slate-400">Industry</div>
                    <div className="text-sm font-medium text-slate-900 dark:text-slate-100">{lead.industry}</div>
                  </div>
                </div>
              )}

              {lead.country && (
                <div className="flex items-start gap-3">
                  <MapPin className="w-5 h-5 text-slate-400 mt-0.5" />
                  <div>
                    <div className="text-xs text-slate-600 dark:text-slate-400">Country</div>
                    <div className="text-sm font-medium text-slate-900 dark:text-slate-100">{lead.country}</div>
                  </div>
                </div>
              )}
            </div>

            {lead.lead_message && (
              <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">Message</div>
                <div className="text-sm text-slate-900 dark:text-slate-100">{lead.lead_message}</div>
              </div>
            )}
          </div>

          {/* Score Breakdown Card */}
          {scoreBreakdown && scoreBreakdown.length > 0 && lead.score_value != null && (
            <ScoreBreakdown breakdown={scoreBreakdown} totalScore={lead.score_value} />
          )}

          {/* Email Draft Section */}
          {drafts.length > 0 ? (
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Mail className="w-5 h-5" />
                  Email Draft
                </h2>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400">
                  <FileText className="w-3 h-3 mr-1" />
                  {VARIANT_LABELS[drafts[0].variant] || drafts[0].variant}
                </span>
              </div>
              <EmailEditor
                draft={drafts[0]}
                onApprove={loadLeadData}
                onReject={loadLeadData}
              />
            </div>
          ) : lead.score_value != null ? (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
                <Mail className="w-5 h-5" />
                Email Draft
              </h2>
              <div className="text-center py-8">
                <Mail className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {lead.recommended_action === 'DISQUALIFY' || lead.recommended_action === 'HOLD'
                    ? 'No email drafted — lead was marked for ' + (lead.recommended_action === 'DISQUALIFY' ? 'disqualification' : 'hold')
                    : 'No email drafted — re-run the pipeline to generate one'
                  }
                </p>
              </div>
            </div>
          ) : null}

          <div className="card p-6">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
              Activity Timeline
            </h2>
            <ActivityTimeline activities={activities} />
          </div>
        </div>

        <div className="space-y-6">
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
              Outcome Stage
            </h2>
            <FeedbackForm
              leadId={leadId}
              currentStage={lead.current_outcome_stage}
              onSuccess={loadLeadData}
            />
          </div>

          {outcomeStages.length > 0 && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
                Stage Timeline
              </h2>
              <StageTimeline stages={outcomeStages} />
            </div>
          )}

          {classifications.length > 1 && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
                Classification History
              </h2>
              <div className="space-y-3">
                {classifications.slice(1).map((c) => (
                  <ReplyClassificationCard
                    key={c.id}
                    leadId={leadId}
                    classificationId={c.id}
                    classification={c.classification}
                    confidence={c.confidence}
                    reasoning={c.reasoning}
                    extractedDates={c.extracted_dates || undefined}
                    isAutoReply={c.is_auto_reply}
                    overriddenClassification={c.overridden_classification}
                    onOverride={loadLeadData}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
