'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, Play, Info } from 'lucide-react';
import { CsvUploadForm } from '@/components/upload/csv-upload-form';
import { getLeads, bulkRunPipeline } from '@/lib/api';

const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === 'true';

export default function UploadPage() {
  const router = useRouter();
  const [uploadedCount, setUploadedCount] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processProgress, setProcessProgress] = useState<string | null>(null);
  const [processError, setProcessError] = useState<string | null>(null);
  const processRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (uploadedCount !== null && processRef.current) {
      processRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [uploadedCount]);

  const handleUploadSuccess = (count: number) => {
    setUploadedCount(count);
  };

  const handleRunPipeline = async () => {
    setIsProcessing(true);
    setProcessError(null);
    setProcessProgress('Fetching unprocessed leads...');

    try {
      // Collect all NEW leads (paginate to get all)
      const allNewLeadIds: string[] = [];
      let cursor: string | undefined;
      let hasMore = true;

      while (hasMore) {
        const response = await getLeads({ status: 'NEW', limit: 100, cursor });
        allNewLeadIds.push(...response.items.map((l) => l.id));
        hasMore = response.has_more;
        cursor = response.next_cursor ?? undefined;
      }

      if (allNewLeadIds.length === 0) {
        setProcessProgress(null);
        setProcessError('No unprocessed leads found.');
        setIsProcessing(false);
        return;
      }

      // Process in batches of 100
      let processed = 0;
      for (let i = 0; i < allNewLeadIds.length; i += 100) {
        const batch = allNewLeadIds.slice(i, i + 100);
        setProcessProgress(`Processing leads ${processed + 1}–${processed + batch.length} of ${allNewLeadIds.length}...`);
        await bulkRunPipeline(batch);
        processed += batch.length;
      }

      setProcessProgress(`Done! ${processed} leads processed.`);
      await new Promise((r) => setTimeout(r, 1500));
      router.refresh();
      router.push('/');
    } catch (err) {
      setProcessError(err instanceof Error ? err.message : 'Pipeline processing failed');
      setProcessProgress(null);
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2 flex items-center gap-3">
          <Upload className="w-8 h-8" />
          Upload Leads
        </h1>
        <p className="text-slate-600 dark:text-slate-400">
          Upload a CSV file containing your leads to process through the pipeline
        </p>
      </div>

      {IS_DEMO && (
        <div className="flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
          <Info className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-900 dark:text-amber-100">
            <p className="font-medium mb-1">Demo Instance</p>
            <p className="text-amber-800 dark:text-amber-200">
              CSV upload is disabled in this demo, but is fully functional in production.
              Explore the pre-loaded leads on the <a href="/" className="underline font-medium">Dashboard</a> to see the full pipeline in action.
            </p>
          </div>
        </div>
      )}

      <div className={`card p-6 ${IS_DEMO ? 'opacity-50 pointer-events-none' : ''}`}>
        <div className="flex items-start gap-3 mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900 dark:text-blue-100">
            <p className="font-medium mb-1">CSV Format Requirements</p>
            <ul className="space-y-1 text-blue-800 dark:text-blue-200">
              <li>Required fields: email, first_name, last_name</li>
              <li>Optional fields: company, job_title, phone, linkedin_url, website, industry, company_size, revenue, location, source, campaign, raw_notes</li>
              <li>First row should contain column headers</li>
              <li>Maximum file size: 10MB</li>
            </ul>
          </div>
        </div>

        <CsvUploadForm onSuccess={handleUploadSuccess} />
      </div>

      {uploadedCount !== null && (
        <div ref={processRef} className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
            <Play className="w-5 h-5" />
            Process Leads
          </h2>

          <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
            {uploadedCount} leads uploaded successfully. Click below to run the pipeline and process all leads through scoring, decision-making, and email drafting.
          </p>

          {processError && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-800 dark:text-red-400">
              {processError}
            </div>
          )}

          {processProgress && (
            <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-sm text-blue-800 dark:text-blue-400">
              {processProgress}
            </div>
          )}

          <button
            onClick={handleRunPipeline}
            disabled={isProcessing}
            className="btn-primary w-full py-3 text-base"
          >
            {isProcessing ? 'Processing...' : 'Run Pipeline'}
          </button>
        </div>
      )}

      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3">
          Pipeline Stages
        </h3>
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center text-xs font-semibold text-blue-600 dark:text-blue-400 flex-shrink-0">
              1
            </div>
            <div>
              <div className="text-sm font-medium text-slate-900 dark:text-slate-100">Normalization</div>
              <div className="text-xs text-slate-600 dark:text-slate-400">Clean and standardize lead data</div>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center text-xs font-semibold text-blue-600 dark:text-blue-400 flex-shrink-0">
              2
            </div>
            <div>
              <div className="text-sm font-medium text-slate-900 dark:text-slate-100">Enrichment</div>
              <div className="text-xs text-slate-600 dark:text-slate-400">Enhance lead data with additional context</div>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center text-xs font-semibold text-blue-600 dark:text-blue-400 flex-shrink-0">
              3
            </div>
            <div>
              <div className="text-sm font-medium text-slate-900 dark:text-slate-100">Scoring</div>
              <div className="text-xs text-slate-600 dark:text-slate-400">Calculate lead quality score</div>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center text-xs font-semibold text-blue-600 dark:text-blue-400 flex-shrink-0">
              4
            </div>
            <div>
              <div className="text-sm font-medium text-slate-900 dark:text-slate-100">Decision</div>
              <div className="text-xs text-slate-600 dark:text-slate-400">Determine next action for each lead</div>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center text-xs font-semibold text-blue-600 dark:text-blue-400 flex-shrink-0">
              5
            </div>
            <div>
              <div className="text-sm font-medium text-slate-900 dark:text-slate-100">Email Draft</div>
              <div className="text-xs text-slate-600 dark:text-slate-400">Generate personalized email for qualified leads</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
