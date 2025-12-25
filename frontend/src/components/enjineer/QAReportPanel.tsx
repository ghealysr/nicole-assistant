'use client';

/**
 * QA Report Panel Component
 * 
 * Displays QA reports for an Enjineer project with:
 * - Issues grouped by severity (critical, high, medium, low)
 * - Click-to-navigate to file/line
 * - Fix suggestions with copy buttons
 * - Re-run QA action button
 * - Historical report comparison
 */

import React, { useEffect, useState, useCallback } from 'react';
import { 
  AlertCircle, 
  AlertTriangle, 
  CheckCircle2, 
  Info, 
  RefreshCw,
  FileCode,
  Copy,
  ChevronDown,
  ChevronRight,
  Clock,
  Zap,
  Shield,
  ExternalLink
} from 'lucide-react';
import { enjineerApi } from '@/lib/enjineer/api';
import type { QAReport, QAIssue } from '@/types/enjineer';
import { useEnjineerStore } from '@/lib/enjineer/store';

// ============================================================================
// Types
// ============================================================================

interface QAReportPanelProps {
  projectId: number | null;
  onFileClick?: (path: string, line?: number) => void;
}

type SeverityLevel = 'critical' | 'high' | 'medium' | 'low';

// ============================================================================
// Severity Configuration
// ============================================================================

const SEVERITY_CONFIG: Record<SeverityLevel, {
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  borderColor: string;
  label: string;
}> = {
  critical: {
    icon: <AlertCircle size={14} />,
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    label: 'Critical'
  },
  high: {
    icon: <AlertTriangle size={14} />,
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
    label: 'High'
  },
  medium: {
    icon: <Info size={14} />,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/30',
    label: 'Medium'
  },
  low: {
    icon: <CheckCircle2 size={14} />,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
    label: 'Low'
  }
};

// ============================================================================
// Issue Card Component
// ============================================================================

function IssueCard({ 
  issue, 
  severity,
  onFileClick 
}: { 
  issue: QAIssue; 
  severity: SeverityLevel;
  onFileClick?: (path: string, line?: number) => void;
}) {
  const [copied, setCopied] = useState(false);
  const config = SEVERITY_CONFIG[severity];
  
  const handleCopyFix = useCallback(() => {
    if (issue.fix) {
      navigator.clipboard.writeText(issue.fix);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [issue.fix]);
  
  const handleFileClick = useCallback(() => {
    if (issue.file && onFileClick) {
      onFileClick(issue.file, issue.line || undefined);
    }
  }, [issue.file, issue.line, onFileClick]);
  
  return (
    <div className={`rounded-lg border ${config.borderColor} ${config.bgColor} p-3 space-y-2`}>
      {/* Issue Header */}
      <div className="flex items-start gap-2">
        <span className={config.color}>{config.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-[#E2E8F0] leading-snug">{issue.issue}</p>
          
          {/* File Location */}
          {issue.file && (
            <button
              onClick={handleFileClick}
              className="mt-1 flex items-center gap-1 text-xs text-[#8B5CF6] hover:text-[#A78BFA] transition-colors"
            >
              <FileCode size={12} />
              <span className="truncate">{issue.file}</span>
              {issue.line && <span className="text-[#64748B]">:{issue.line}</span>}
              <ExternalLink size={10} className="ml-1" />
            </button>
          )}
        </div>
        
        {/* Category Badge */}
        {issue.category && (
          <span className="flex-shrink-0 px-2 py-0.5 text-[10px] font-medium rounded bg-[#1E1E2E] text-[#94A3B8] border border-[#2E2E3E]">
            {issue.category}
          </span>
        )}
      </div>
      
      {/* Suggested Fix */}
      {issue.fix && (
        <div className="mt-2 p-2 rounded bg-[#0D0D14] border border-[#2E2E3E]">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] uppercase tracking-wider text-[#64748B] font-medium">Suggested Fix</span>
            <button
              onClick={handleCopyFix}
              className="flex items-center gap-1 text-[10px] text-[#8B5CF6] hover:text-[#A78BFA] transition-colors"
            >
              <Copy size={10} />
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <p className="text-xs text-[#94A3B8] leading-relaxed">{issue.fix}</p>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Severity Section Component
// ============================================================================

function SeveritySection({ 
  severity, 
  issues,
  onFileClick,
  defaultExpanded = false
}: { 
  severity: SeverityLevel;
  issues: QAIssue[];
  onFileClick?: (path: string, line?: number) => void;
  defaultExpanded?: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const config = SEVERITY_CONFIG[severity];
  
  if (issues.length === 0) return null;
  
  return (
    <div className="space-y-2">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 py-2 px-1 hover:bg-[#1E1E2E]/50 rounded transition-colors"
      >
        {isExpanded ? (
          <ChevronDown size={14} className="text-[#64748B]" />
        ) : (
          <ChevronRight size={14} className="text-[#64748B]" />
        )}
        <span className={config.color}>{config.icon}</span>
        <span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
        <span className="ml-auto px-2 py-0.5 text-xs rounded-full bg-[#1E1E2E] text-[#94A3B8]">
          {issues.length}
        </span>
      </button>
      
      {isExpanded && (
        <div className="pl-6 space-y-2">
          {issues.map((issue, idx) => (
            <IssueCard 
              key={`${issue.file}-${issue.line}-${idx}`}
              issue={issue}
              severity={severity}
              onFileClick={onFileClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Report Summary Component
// ============================================================================

function ReportSummary({ report }: { report: QAReport }) {
  const statusColor = report.status === 'pass' 
    ? 'text-green-400' 
    : report.status === 'fail' 
    ? 'text-red-400' 
    : 'text-yellow-400';
  
  const statusBg = report.status === 'pass' 
    ? 'bg-green-500/10' 
    : report.status === 'fail' 
    ? 'bg-red-500/10' 
    : 'bg-yellow-500/10';
  
  return (
    <div className={`rounded-lg ${statusBg} border border-[#2E2E3E] p-4 space-y-3`}>
      {/* Status Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {report.status === 'pass' ? (
            <CheckCircle2 size={20} className="text-green-400" />
          ) : report.status === 'fail' ? (
            <AlertCircle size={20} className="text-red-400" />
          ) : (
            <AlertTriangle size={20} className="text-yellow-400" />
          )}
          <span className={`text-lg font-semibold ${statusColor}`}>
            {report.status === 'pass' ? 'QA Passed' : report.status === 'fail' ? 'QA Failed' : 'Partial Pass'}
          </span>
        </div>
        
        {/* Model Badge */}
        {report.modelUsed && (
          <span className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-[#1E1E2E] text-[#8B5CF6] border border-[#2E2E3E]">
            <Zap size={10} />
            {report.modelUsed.includes('opus') ? 'Senior QA' : report.modelUsed.includes('gpt') ? 'Standard QA' : 'QA'}
          </span>
        )}
      </div>
      
      {/* Stats Row */}
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1 text-red-400">
          <AlertCircle size={12} />
          <span>{report.counts.blocking} Blocking</span>
        </div>
        <div className="flex items-center gap-1 text-yellow-400">
          <AlertTriangle size={12} />
          <span>{report.counts.warnings} Warnings</span>
        </div>
        <div className="flex items-center gap-1 text-green-400">
          <CheckCircle2 size={12} />
          <span>{report.counts.passed} Passed</span>
        </div>
        {report.durationSeconds && (
          <div className="flex items-center gap-1 text-[#64748B] ml-auto">
            <Clock size={12} />
            <span>{report.durationSeconds}s</span>
          </div>
        )}
      </div>
      
      {/* Summary */}
      {report.summary && (
        <p className="text-sm text-[#94A3B8] leading-relaxed">{report.summary}</p>
      )}
      
      {/* Cost (if tracked) */}
      {report.estimatedCostUsd && report.estimatedCostUsd > 0 && (
        <div className="text-[10px] text-[#64748B]">
          Cost: ${report.estimatedCostUsd.toFixed(4)}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function QAReportPanel({ projectId, onFileClick }: QAReportPanelProps) {
  const [reports, setReports] = useState<QAReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedReportIdx, setSelectedReportIdx] = useState(0);
  
  const { selectFile } = useEnjineerStore();
  
  // Fetch QA reports
  const fetchReports = useCallback(async () => {
    if (!projectId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await enjineerApi.getQAReports(projectId, { limit: 10 });
      setReports(response.reports);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load QA reports');
    } finally {
      setLoading(false);
    }
  }, [projectId]);
  
  useEffect(() => {
    fetchReports();
  }, [fetchReports]);
  
  // Handle file navigation
  const handleFileClick = useCallback((path: string, line?: number) => {
    // Use provided callback or default to store action
    if (onFileClick) {
      onFileClick(path, line);
    } else {
      // Normalize path and select in editor
      const normalizedPath = path.startsWith('/') ? path : `/${path}`;
      selectFile(normalizedPath);
    }
  }, [onFileClick, selectFile]);
  
  // No project selected
  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <Shield size={48} className="text-[#2E2E3E] mb-4" />
        <p className="text-[#64748B] text-sm">Select a project to view QA reports</p>
      </div>
    );
  }
  
  // Loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <RefreshCw size={24} className="text-[#8B5CF6] animate-spin mb-3" />
        <p className="text-[#64748B] text-sm">Loading QA reports...</p>
      </div>
    );
  }
  
  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <AlertCircle size={48} className="text-red-400/50 mb-4" />
        <p className="text-red-400 text-sm mb-2">{error}</p>
        <button
          onClick={fetchReports}
          className="text-xs text-[#8B5CF6] hover:text-[#A78BFA] flex items-center gap-1"
        >
          <RefreshCw size={12} />
          Try again
        </button>
      </div>
    );
  }
  
  // No reports
  if (reports.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <Shield size={48} className="text-[#2E2E3E] mb-4" />
        <p className="text-[#94A3B8] text-sm mb-2">No QA reports yet</p>
        <p className="text-[#64748B] text-xs">
          Ask Nicole to run a QA review on your code
        </p>
      </div>
    );
  }
  
  const selectedReport = reports[selectedReportIdx];
  
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-[#2E2E3E] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield size={16} className="text-[#8B5CF6]" />
          <h3 className="text-sm font-semibold text-[#E2E8F0]">QA Reports</h3>
          <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#1E1E2E] text-[#64748B]">
            {reports.length}
          </span>
        </div>
        
        <button
          onClick={fetchReports}
          className="p-1.5 rounded hover:bg-[#1E1E2E] transition-colors"
          title="Refresh reports"
        >
          <RefreshCw size={14} className="text-[#64748B]" />
        </button>
      </div>
      
      {/* Report Selector (if multiple reports) */}
      {reports.length > 1 && (
        <div className="flex-shrink-0 p-2 border-b border-[#2E2E3E] overflow-x-auto">
          <div className="flex gap-1">
            {reports.map((report, idx) => (
              <button
                key={report.id}
                onClick={() => setSelectedReportIdx(idx)}
                className={`
                  flex-shrink-0 px-3 py-1.5 text-xs rounded transition-colors
                  ${idx === selectedReportIdx 
                    ? 'bg-[#8B5CF6] text-white' 
                    : 'bg-[#1E1E2E] text-[#94A3B8] hover:bg-[#2E2E3E]'}
                `}
              >
                {report.triggerType === 'senior_qa' ? 'SR QA' : 'QA'} #{reports.length - idx}
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Report Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Summary */}
        <ReportSummary report={selectedReport} />
        
        {/* Issues by Severity */}
        <div className="space-y-2">
          <SeveritySection 
            severity="critical" 
            issues={selectedReport.issues.critical}
            onFileClick={handleFileClick}
            defaultExpanded={true}
          />
          <SeveritySection 
            severity="high" 
            issues={selectedReport.issues.high}
            onFileClick={handleFileClick}
            defaultExpanded={true}
          />
          <SeveritySection 
            severity="medium" 
            issues={selectedReport.issues.medium}
            onFileClick={handleFileClick}
            defaultExpanded={false}
          />
          <SeveritySection 
            severity="low" 
            issues={selectedReport.issues.low}
            onFileClick={handleFileClick}
            defaultExpanded={false}
          />
        </div>
        
        {/* Timestamp */}
        {selectedReport.createdAt && (
          <div className="text-[10px] text-[#64748B] text-center pt-4">
            Report generated: {new Date(selectedReport.createdAt).toLocaleString()}
          </div>
        )}
      </div>
    </div>
  );
}

export default QAReportPanel;

