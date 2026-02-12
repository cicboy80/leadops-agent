'use client';

import { useEffect, useState } from 'react';
import { Settings, Save, AlertCircle, CheckCircle2 } from 'lucide-react';
import { getScoringConfig, updateScoringConfig } from '@/lib/api';
import type { ScoringConfig } from '@/lib/types';

export default function SettingsPage() {
  const [config, setConfig] = useState<ScoringConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await getScoringConfig();
      setConfig(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load configuration');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;

    setIsSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const updated = await updateScoringConfig(config);
      setConfig(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setIsSaving(false);
    }
  };

  const updateWeight = (key: string, value: number) => {
    if (!config) return;
    setConfig({
      ...config,
      weights: {
        ...config.weights,
        [key]: value,
      },
    });
  };

  const updateThreshold = (key: string, value: number) => {
    if (!config) return;
    setConfig({
      ...config,
      thresholds: {
        ...config.thresholds,
        [key]: value,
      },
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-600 dark:text-slate-400">Loading...</div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-800 dark:text-red-400">
        <AlertCircle className="w-5 h-5 flex-shrink-0" />
        Failed to load configuration
      </div>
    );
  }

  const weightFields: Array<{ key: string; label: string }> = [
    { key: 'urgency', label: 'Urgency Keywords' },
    { key: 'budget', label: 'Budget Indicators' },
    { key: 'company_size', label: 'Company Size' },
    { key: 'pain_point', label: 'Pain Point Keywords' },
    { key: 'job_title', label: 'Job Title' },
    { key: 'industry', label: 'Industry' },
    { key: 'source', label: 'Source' },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2 flex items-center gap-3">
          <Settings className="w-8 h-8" />
          Settings
        </h1>
        <p className="text-slate-600 dark:text-slate-400">
          Configure scoring weights and thresholds for lead qualification
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-800 dark:text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-sm text-green-800 dark:text-green-400">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          Configuration saved successfully
        </div>
      )}

      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-6">
          Scoring Weights
        </h2>

        <div className="space-y-6">
          {weightFields.map(({ key, label }) => (
            <div key={key}>
              <div className="flex items-center justify-between mb-2">
                <label className="label">{label}</label>
                <span className="text-sm font-medium text-slate-900 dark:text-slate-100 min-w-[3rem] text-right">
                  {(config.weights[key] ?? 0).toFixed(1)}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="10"
                step="0.1"
                value={config.weights[key] ?? 0}
                onChange={(e) => updateWeight(key, parseFloat(e.target.value))}
                className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-1">
                <span>0</span>
                <span>10</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-6">
          Score Thresholds
        </h2>

        {/* Threshold Visualization */}
        <div className="mb-8">
          <div className="relative h-8 rounded-full overflow-hidden flex">
            <div
              className="bg-blue-400 dark:bg-blue-600 transition-all"
              style={{ width: `${config.thresholds.warm}%` }}
            />
            <div
              className="bg-amber-400 dark:bg-amber-600 transition-all"
              style={{ width: `${config.thresholds.hot - config.thresholds.warm}%` }}
            />
            <div
              className="bg-red-400 dark:bg-red-600 transition-all flex-1"
            />
          </div>
          <div className="flex justify-between mt-2">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-blue-400 dark:bg-blue-600" />
              <span className="text-xs text-slate-600 dark:text-slate-400">Cold (0–{config.thresholds.warm - 1})</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-amber-400 dark:bg-amber-600" />
              <span className="text-xs text-slate-600 dark:text-slate-400">Warm ({config.thresholds.warm}–{config.thresholds.hot - 1})</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-400 dark:bg-red-600" />
              <span className="text-xs text-slate-600 dark:text-slate-400">Hot ({config.thresholds.hot}–100)</span>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div>
            <label className="label mb-2 block">
              Hot Lead Threshold
            </label>
            <input
              type="number"
              min="0"
              max="100"
              value={config.thresholds.hot}
              onChange={(e) => updateThreshold('hot', parseInt(e.target.value))}
              className="input"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Leads with a score above this value are classified as HOT
            </p>
          </div>

          <div>
            <label className="label mb-2 block">
              Warm Lead Threshold
            </label>
            <input
              type="number"
              min="0"
              max="100"
              value={config.thresholds.warm}
              onChange={(e) => updateThreshold('warm', parseInt(e.target.value))}
              className="input"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Leads with a score above this value (but below hot threshold) are classified as WARM
            </p>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-3">
        <button
          onClick={loadConfig}
          disabled={isSaving}
          className="btn-outline"
        >
          Reset
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="btn-primary flex items-center gap-2"
        >
          <Save className="w-4 h-4" />
          {isSaving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {config.updated_at && (
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center">
          Last updated: {new Date(config.updated_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}
