import React, { useState } from 'react';
import { useVibeProject } from '@/lib/hooks/useVibeProject';
import { MessageSquare, AlertCircle, Zap, Palette, Send } from 'lucide-react';

interface VibeFeedbackInputProps {
  projectId: number;
  onSubmitted: () => void;
}

export function VibeFeedbackInput({ projectId, onSubmitted }: VibeFeedbackInputProps) {
  const { submitFeedback } = useVibeProject();
  const [description, setDescription] = useState('');
  const [type, setType] = useState<'bug_fix' | 'design_change' | 'feature_add'>('bug_fix');
  const [priority, setPriority] = useState('medium');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!description.trim()) return;
    setLoading(true);
    try {
      const success = await submitFeedback(projectId, {
        feedback_type: type,
        description,
        priority,
        category: type === 'bug_fix' ? 'functional' : type === 'design_change' ? 'visual' : 'functional',
        affected_pages: [] 
      });

      if (success) {
        setDescription('');
        onSubmitted();
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="vibe-feedback-input bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="bg-gray-50 p-4 border-b border-gray-100 flex justify-between items-center">
        <h3 className="font-semibold text-gray-900 flex items-center">
          <MessageSquare size={18} className="mr-2 text-purple-600" />
          Submit Feedback
        </h3>
      </div>
      
      <div className="p-4 space-y-4">
        {/* Type Selector */}
        <div className="flex space-x-2">
          {([
            { id: 'bug_fix' as const, label: 'Bug Fix', icon: AlertCircle, color: 'text-red-600 bg-red-50 border-red-200' },
            { id: 'design_change' as const, label: 'Design Tweak', icon: Palette, color: 'text-blue-600 bg-blue-50 border-blue-200' },
            { id: 'feature_add' as const, label: 'New Feature', icon: Zap, color: 'text-yellow-600 bg-yellow-50 border-yellow-200' }
          ] as const).map(opt => (
            <button
              key={opt.id}
              onClick={() => setType(opt.id)}
              className={`flex-1 py-2 px-3 rounded-lg border text-sm font-medium flex items-center justify-center transition-all
                ${type === opt.id ? `${opt.color} ring-1 ring-offset-1` : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'}`}
            >
              <opt.icon size={14} className="mr-2" />
              {opt.label}
            </button>
          ))}
        </div>

        {/* Priority */}
        <div>
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1 block">Priority</label>
          <select 
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="w-full p-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
          >
            <option value="low">Low - Nice to have</option>
            <option value="medium">Medium - Should fix</option>
            <option value="high">High - Important</option>
            <option value="critical">Critical - Blocker</option>
          </select>
        </div>

        {/* Description */}
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe the issue or change request..."
          className="w-full p-3 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 min-h-[100px]"
        />

        <div className="flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={!description.trim() || loading}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center shadow-sm"
          >
            <Send size={16} className="mr-2" />
            {loading ? 'Sending...' : 'Submit Feedback'}
          </button>
        </div>
      </div>
    </div>
  );
}

