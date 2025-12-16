import React from 'react';
import { Clock, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export interface Iteration {
  iteration_id: number;
  iteration_number: number;
  iteration_type: string;
  feedback: string;
  status: string;
  created_at: string;
  resolved_at?: string;
  changes_summary?: string;
}

interface VibeIterationHistoryProps {
  iterations: Array<Record<string, unknown>>;
  currentIteration: number;
}

/**
 * Transforms raw API data to typed Iteration
 */
function toIteration(data: Record<string, unknown>): Iteration {
  return {
    iteration_id: (data.iteration_id as number) || 0,
    iteration_number: (data.iteration_number as number) || 0,
    iteration_type: (data.iteration_type as string) || 'bug_fix',
    feedback: (data.feedback as string) || '',
    status: (data.status as string) || 'pending',
    created_at: (data.created_at as string) || new Date().toISOString(),
    resolved_at: data.resolved_at as string | undefined,
    changes_summary: data.changes_summary as string | undefined,
  };
}

function IterationItem({ iteration, isCurrent }: { iteration: Iteration; isCurrent: boolean }) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'resolved': return <CheckCircle2 size={16} className="text-green-500" />;
      case 'in_progress': return <RefreshCw size={16} className="text-blue-500 animate-spin" />;
      case 'pending': return <Clock size={16} className="text-gray-400" />;
      default: return <AlertCircle size={16} className="text-red-500" />;
    }
  };

  return (
    <div className={`relative pl-8 pb-8 last:pb-0 ${isCurrent ? 'opacity-100' : 'opacity-70 hover:opacity-100 transition-opacity'}`}>
      {/* Timeline Line */}
      <div className="absolute left-3 top-8 bottom-0 w-0.5 bg-gray-200" />
      
      {/* Timeline Dot */}
      <div className={`absolute left-0 top-0 w-6 h-6 rounded-full border-2 flex items-center justify-center bg-white z-10
        ${iteration.status === 'resolved' ? 'border-green-500' : 'border-gray-300'}`}>
        {getStatusIcon(iteration.status)}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        <div className="flex justify-between items-start mb-2">
          <div>
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Iteration #{iteration.iteration_number}</span>
            <h4 className="text-sm font-semibold text-gray-900 capitalize">{iteration.iteration_type.replace('_', ' ')}</h4>
          </div>
          <span className="text-xs text-gray-400">{new Date(iteration.created_at).toLocaleDateString()}</span>
        </div>
        
        <p className="text-sm text-gray-700 mb-3 bg-gray-50 p-2 rounded italic">&ldquo;{iteration.feedback}&rdquo;</p>
        
        {iteration.changes_summary && (
          <div className="text-xs text-green-700 bg-green-50 p-2 rounded border border-green-100">
            <strong>Fix:</strong> {iteration.changes_summary}
          </div>
        )}
      </div>
    </div>
  );
}

export function VibeIterationHistory({ iterations, currentIteration }: VibeIterationHistoryProps) {
  if (!iterations.length) return null;
  
  // Transform raw data to typed iterations
  const typedIterations = iterations.map(toIteration);

  return (
    <div className="vibe-iteration-history">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Iteration History</h3>
      <div className="vibe-timeline">
        {typedIterations.map(iter => (
          <IterationItem 
            key={iter.iteration_id} 
            iteration={iter} 
            isCurrent={iter.iteration_number === currentIteration}
          />
        ))}
      </div>
    </div>
  );
}

