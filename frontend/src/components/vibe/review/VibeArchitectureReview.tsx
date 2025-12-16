import React, { useState } from 'react';
import { useVibeProject } from '@/lib/hooks/useVibeProject';
import { CheckCircle2, AlertCircle, MessageSquare } from 'lucide-react';

interface VibeArchitectureReviewProps {
  projectId: number;
  architecture: Record<string, unknown>;
  onApprove: () => void;
}

export function VibeArchitectureReview({ projectId, architecture, onApprove }: VibeArchitectureReviewProps) {
  const { approveArchitecture, requestArchitectureRevision, operationStates } = useVibeProject();
  const [feedback, setFeedback] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);

  const handleApprove = async () => {
    // Assuming current user context is handled by hook/backend
    const success = await approveArchitecture(projectId, 'current_user'); 
    if (success) {
      onApprove();
    }
  };

  const handleReject = async () => {
    if (!feedback.trim()) return;
    const success = await requestArchitectureRevision(projectId, feedback, 'current_user');
    if (success) {
      setFeedback('');
      setShowRejectForm(false);
    }
  };

  return (
    <div className="vibe-arch-review bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
        <div>
          <h3 className="font-semibold text-gray-900">Architecture Review</h3>
          <p className="text-xs text-gray-500">Review the proposed structure before building</p>
        </div>
        <div className="flex space-x-2">
          {!showRejectForm && (
            <>
              <button 
                onClick={() => setShowRejectForm(true)}
                className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Request Changes
              </button>
              <button 
                onClick={handleApprove}
                disabled={operationStates.approve.loading}
                className="px-3 py-1.5 text-sm text-white bg-green-600 hover:bg-green-700 rounded-md flex items-center shadow-sm"
              >
                {operationStates.approve.loading ? 'Approving...' : (
                  <><CheckCircle2 size={16} className="mr-1.5" /> Approve Plan</>
                )}
              </button>
            </>
          )}
        </div>
      </div>

      <div className="p-4">
        {/* Visual Architecture Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
            <h4 className="text-xs font-semibold text-blue-800 uppercase tracking-wider mb-2">Pages</h4>
            <ul className="space-y-1">
              {(architecture?.pages as Array<{ path: string; components?: unknown[] }> | undefined)?.map((page, idx: number) => (
                <li key={idx} className="text-sm text-blue-900 flex items-center">
                  <span className="w-1.5 h-1.5 bg-blue-400 rounded-full mr-2"></span>
                  {page.path} <span className="text-blue-400 ml-1 text-xs">({page.components?.length || 0} components)</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
            <h4 className="text-xs font-semibold text-purple-800 uppercase tracking-wider mb-2">Design System</h4>
            <div className="flex flex-wrap gap-2 mb-2">
              <span className="text-xs px-2 py-1 bg-white rounded border border-purple-200 text-purple-700">
                Primary: {(architecture?.design_system as Record<string, unknown> | undefined)?.colors ? ((architecture.design_system as Record<string, unknown>).colors as Record<string, unknown>).primary as string : 'N/A'}
              </span>
              <span className="text-xs px-2 py-1 bg-white rounded border border-purple-200 text-purple-700">
                Font: {(architecture?.design_system as Record<string, unknown> | undefined)?.typography ? ((architecture.design_system as Record<string, unknown>).typography as Record<string, unknown>).heading_font as string : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Reject Form */}
        {showRejectForm && (
          <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-100 animate-in fade-in slide-in-from-top-2">
            <h4 className="text-sm font-semibold text-red-800 mb-2 flex items-center">
              <AlertCircle size={16} className="mr-2" />
              What needs to change?
            </h4>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="E.g., The color scheme is too dark, we need a services page..."
              className="w-full p-2 text-sm border border-red-200 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 mb-2"
              rows={3}
            />
            <div className="flex justify-end space-x-2">
              <button 
                onClick={() => setShowRejectForm(false)}
                className="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-900"
              >
                Cancel
              </button>
              <button 
                onClick={handleReject}
                disabled={!feedback.trim()}
                className="px-3 py-1.5 text-xs text-white bg-red-600 hover:bg-red-700 rounded-md flex items-center"
              >
                <MessageSquare size={14} className="mr-1.5" />
                Submit Feedback
              </button>
            </div>
          </div>
        )}

        {/* Raw JSON Toggle */}
        <details className="mt-4 text-xs">
          <summary className="cursor-pointer text-gray-500 hover:text-gray-700">View Raw Specification</summary>
          <pre className="mt-2 p-3 bg-gray-900 text-gray-300 rounded-lg overflow-x-auto">
            {JSON.stringify(architecture, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  );
}

