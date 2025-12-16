import React, { useState } from 'react';
import { Plus, Trash2, Globe, Link as LinkIcon } from 'lucide-react';

interface Competitor {
  url: string;
  notes?: string;
}

interface VibeCompetitorInputProps {
  competitors: Competitor[];
  onChange: (competitors: Competitor[]) => void;
}

export function VibeCompetitorInput({ competitors, onChange }: VibeCompetitorInputProps) {
  const [newUrl, setNewUrl] = useState('');
  const [newNotes, setNewNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  const isValidUrl = (url: string) => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const handleAdd = () => {
    if (!newUrl) return;
    
    let formattedUrl = newUrl;
    if (!formattedUrl.startsWith('http')) {
      formattedUrl = `https://${formattedUrl}`;
    }

    if (!isValidUrl(formattedUrl)) {
      setError('Please enter a valid URL');
      return;
    }

    onChange([...competitors, { url: formattedUrl, notes: newNotes }]);
    setNewUrl('');
    setNewNotes('');
    setError(null);
  };

  const handleRemove = (index: number) => {
    const newCompetitors = [...competitors];
    newCompetitors.splice(index, 1);
    onChange(newCompetitors);
  };

  return (
    <div className="vibe-competitor-input">
      <label className="block text-sm font-medium mb-2 text-gray-700">Competitor / Inspiration Sites</label>
      
      {/* List */}
      <div className="space-y-2 mb-4">
        {competitors.map((comp, idx) => (
          <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center space-x-3 overflow-hidden">
              <div className="bg-white p-1.5 rounded-full border border-gray-200">
                <Globe size={16} className="text-gray-500" />
              </div>
              <div className="min-w-0">
                <a href={comp.url} target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-blue-600 hover:underline truncate block">
                  {comp.url}
                </a>
                {comp.notes && <p className="text-xs text-gray-500 truncate">{comp.notes}</p>}
              </div>
            </div>
            <button
              onClick={() => handleRemove(idx)}
              className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>

      {/* Add Form */}
      <div className="flex flex-col space-y-2">
        <div className="flex space-x-2">
          <div className="relative flex-1">
            <LinkIcon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            />
          </div>
          <button
            onClick={handleAdd}
            disabled={!newUrl}
            className="px-4 py-2 bg-gray-900 text-white rounded-md text-sm font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            <Plus size={16} className="mr-1" /> Add
          </button>
        </div>
        <input
          type="text"
          value={newNotes}
          onChange={(e) => setNewNotes(e.target.value)}
          placeholder="What do you like about this site?"
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
        />
        {error && <p className="text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}

