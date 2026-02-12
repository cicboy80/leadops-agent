'use client';

import { useState } from 'react';
import { Play, Loader2 } from 'lucide-react';
import { getLeads, bulkRunPipeline } from '@/lib/api';

interface ProcessLeadsButtonProps {
  onProcessingComplete?: () => void;
}

export function ProcessLeadsButton({ onProcessingComplete }: ProcessLeadsButtonProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleProcess = async () => {
    setIsProcessing(true);
    setError(null);
    setProgress('Fetching unprocessed leads...');

    try {
      const allNewLeadIds: string[] = [];
      let cursor: string | undefined;
      let hasMore = true;

      while (hasMore) {
        const response = await getLeads({ status: 'NEW', limit: 100, cursor });
        // Only include leads that haven't been scored yet
        const unscored = response.items.filter((l) => l.score_value === null || l.score_value === undefined);
        allNewLeadIds.push(...unscored.map((l) => l.id));
        hasMore = response.has_more;
        cursor = response.next_cursor ?? undefined;
      }

      if (allNewLeadIds.length === 0) {
        setProgress(null);
        setError('No unprocessed leads found.');
        setIsProcessing(false);
        return;
      }

      let processed = 0;
      for (let i = 0; i < allNewLeadIds.length; i += 100) {
        const batch = allNewLeadIds.slice(i, i + 100);
        setProgress(`Processing ${processed + 1}–${processed + batch.length} of ${allNewLeadIds.length}...`);
        await bulkRunPipeline(batch);
        processed += batch.length;
      }

      setProgress(`Done! ${processed} leads processed. Refreshing...`);
      if (onProcessingComplete) {
        try {
          await onProcessingComplete();
        } catch {
          // Refresh may fail if data is still settling — retry once
        }
      }
      setProgress(null);
      setIsProcessing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
      setProgress(null);
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex items-center gap-3">
      {progress && (
        <span className="text-sm text-blue-600 dark:text-blue-400">{progress}</span>
      )}
      {error && (
        <span className="text-sm text-red-600 dark:text-red-400">{error}</span>
      )}
      <button
        onClick={handleProcess}
        disabled={isProcessing}
        className="btn-secondary flex items-center gap-2"
      >
        {isProcessing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <Play className="w-4 h-4" />
            Process Unscored Leads
          </>
        )}
      </button>
    </div>
  );
}
