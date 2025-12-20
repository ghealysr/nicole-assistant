/**
 * Nicole V7 - Workflow Progress Component
 * 
 * Displays progress for multi-step workflow executions.
 * Shows step-by-step progress with status indicators.
 * 
 * Author: Nicole V7 Frontend
 * Date: December 20, 2025
 */

'use client';

import React, { memo } from 'react';
import { Check, X, Loader2, Clock } from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface WorkflowStep {
  step_number: number;
  step_name: string;
  tool: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  duration_ms?: number;
  error?: string;
}

interface WorkflowProgressProps {
  workflowName: string;
  currentStep: number;
  totalSteps: number;
  steps: WorkflowStep[];
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  error?: string;
}

// ============================================================================
// STATUS ICON COMPONENT
// ============================================================================

const StepStatusIcon = memo(function StepStatusIcon({ 
  status 
}: { 
  status: WorkflowStep['status'] 
}) {
  switch (status) {
    case 'completed':
      return <Check className="w-4 h-4 text-green-500" />;
    case 'failed':
      return <X className="w-4 h-4 text-red-500" />;
    case 'running':
      return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
    case 'pending':
      return <Clock className="w-4 h-4 text-gray-400" />;
    case 'skipped':
      return <div className="w-4 h-4 text-gray-300">−</div>;
    default:
      return null;
  }
});

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export const WorkflowProgress = memo(function WorkflowProgress({
  workflowName,
  currentStep,
  totalSteps,
  steps,
  status,
  error
}: WorkflowProgressProps) {
  const progressPercent = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0;
  
  return (
    <div className="workflow-progress rounded-lg border border-purple-200 bg-purple-50/30 p-3 text-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="text-purple-700 font-medium">
            {workflowName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </div>
          {status === 'running' && (
            <Loader2 className="w-4 h-4 text-purple-500 animate-spin" />
          )}
          {status === 'completed' && (
            <Check className="w-4 h-4 text-green-500" />
          )}
          {status === 'failed' && (
            <X className="w-4 h-4 text-red-500" />
          )}
        </div>
        
        <div className="text-purple-600 text-xs">
          Step {currentStep}/{totalSteps}
        </div>
      </div>
      
      {/* Progress Bar */}
      <div className="mb-3">
        <div className="h-1.5 bg-purple-100 rounded-full overflow-hidden">
          <div 
            className="h-full bg-purple-500 transition-all duration-300 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>
      
      {/* Steps List */}
      {steps.length > 0 && (
        <div className="space-y-1.5">
          {steps.map((step) => (
            <div 
              key={step.step_number}
              className={`
                flex items-center justify-between gap-2 px-2 py-1.5 rounded
                ${step.status === 'running' ? 'bg-blue-50' : ''}
                ${step.status === 'failed' ? 'bg-red-50' : ''}
              `}
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <StepStatusIcon status={step.status} />
                <span className="text-gray-700 truncate">
                  {step.step_name || step.tool}
                </span>
              </div>
              
              {step.duration_ms && step.status === 'completed' && (
                <span className="text-xs text-gray-500">
                  {step.duration_ms}ms
                </span>
              )}
              
              {step.error && step.status === 'failed' && (
                <span className="text-xs text-red-600 truncate max-w-[150px]">
                  {step.error}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
      
      {/* Error Message */}
      {error && status === 'failed' && (
        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          <div className="font-medium mb-1">Workflow Failed</div>
          <div className="text-red-600">{error}</div>
        </div>
      )}
    </div>
  );
});

export default WorkflowProgress;

