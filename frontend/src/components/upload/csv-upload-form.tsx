'use client';

import { useState, useRef, DragEvent } from 'react';
import { Upload, File, CheckCircle2, AlertCircle, X } from 'lucide-react';
import { uploadCSV } from '@/lib/api';

interface CsvUploadFormProps {
  onSuccess?: (count: number) => void;
}

export function CsvUploadForm({ onSuccess }: CsvUploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (!file.name.endsWith('.csv')) {
      return 'Please upload a CSV file';
    }
    if (file.size > 10 * 1024 * 1024) {
      return 'File size must be less than 10MB';
    }
    return null;
  };

  const handleFileSelect = (selectedFile: File) => {
    const validationError = validateFile(selectedFile);
    if (validationError) {
      setError(validationError);
      return;
    }

    setFile(selectedFile);
    setError(null);
    setSuccess(null);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccess(null);
    setProgress(0);

    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 10;
      });
    }, 200);

    try {
      const result = await uploadCSV(file);
      clearInterval(progressInterval);
      setProgress(100);
      setSuccess(`Successfully uploaded ${result.created} leads`);
      setFile(null);

      if (onSuccess) {
        onSuccess(result.created);
      }

      setTimeout(() => {
        setProgress(0);
        setSuccess(null);
      }, 5000);
    } catch (err) {
      clearInterval(progressInterval);
      setProgress(0);
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    setError(null);
    setSuccess(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-6">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center transition-colors
          ${isDragging
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-slate-300 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-600'
          }
        `}
      >
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
            <Upload className="w-8 h-8 text-slate-600 dark:text-slate-400" />
          </div>

          <div>
            <p className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-1">
              Drop your CSV file here
            </p>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              or click to browse
            </p>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileInputChange}
            className="hidden"
            id="file-upload"
          />

          <label htmlFor="file-upload" className="btn-primary cursor-pointer">
            Select File
          </label>

          <p className="text-xs text-slate-500 dark:text-slate-400">
            CSV files only, max 10MB
          </p>
        </div>
      </div>

      {file && (
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center">
                <File className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                  {file.name}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {(file.size / 1024).toFixed(2)} KB
                </p>
              </div>
            </div>
            <button
              onClick={handleRemoveFile}
              disabled={isUploading}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {isUploading && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-600 dark:text-slate-400">Uploading...</span>
            <span className="text-slate-900 dark:text-slate-100 font-medium">{progress}%</span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
            <div
              className="bg-blue-600 h-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-800 dark:text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-sm text-green-800 dark:text-green-400">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          {success}
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={!file || isUploading}
        className="btn-primary w-full py-3 text-base"
      >
        {isUploading ? 'Uploading...' : 'Upload & Process'}
      </button>
    </div>
  );
}
