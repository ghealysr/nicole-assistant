'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

interface AlphawaveDashPanelProps {
  isOpen: boolean;
  onClose: () => void;
  width: number;
  onWidthChange: (width: number) => void;
}

const MIN_WIDTH = 320;
const MAX_WIDTH_PERCENT = 0.75;
const MIN_CHAT_WIDTH = 400;

/**
 * Dashboard panel component for Nicole V7.
 * 
 * Features:
 * - Slides in from the right
 * - Resizable via drag handle
 * - Multiple tabs (Overview, Memory, Artifacts)
 * - Widget cards with stats
 */
export function AlphawaveDashPanel({ isOpen, onClose, width, onWidthChange }: AlphawaveDashPanelProps) {
  const [activeTab, setActiveTab] = useState('overview');
  const [isResizing, setIsResizing] = useState(false);
  const resizeRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing) return;
    const diff = startXRef.current - e.clientX;
    const sidebarWidth = 240;
    const availableWidth = window.innerWidth - sidebarWidth - MIN_CHAT_WIDTH;
    const maxWidth = Math.min(availableWidth, window.innerWidth * MAX_WIDTH_PERCENT);
    const newWidth = Math.max(MIN_WIDTH, Math.min(maxWidth, startWidthRef.current + diff));
    onWidthChange(newWidth);
  }, [isResizing, onWidthChange]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
    document.body.classList.remove('resizing');
  }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = width;
    document.body.classList.add('resizing');
  };

  // Update CSS variable for dashboard width
  useEffect(() => {
    document.documentElement.style.setProperty('--dashboard-width', `${width}px`);
  }, [width]);

  return (
    <aside 
      className={`dashboard-panel ${isOpen ? 'open' : ''}`}
      style={{ width: isOpen ? width : 0 }}
    >
      {/* Resize handle */}
      <div 
        ref={resizeRef}
        className={`dashboard-resize-handle ${isResizing ? 'dragging' : ''}`}
        onMouseDown={startResize}
      />
      
      <div className="flex flex-col h-full" style={{ width, minWidth: width }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#E8E6DC] bg-[#FAF9F6] shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-lavender to-lavender-text flex items-center justify-center">
              <svg viewBox="0 0 24 24" fill="none" className="w-[18px] h-[18px] stroke-white" strokeWidth={2}>
                <rect x="3" y="3" width="7" height="9" rx="1"/>
                <rect x="14" y="3" width="7" height="5" rx="1"/>
                <rect x="14" y="12" width="7" height="9" rx="1"/>
                <rect x="3" y="16" width="7" height="5" rx="1"/>
              </svg>
            </div>
            <span className="text-base font-semibold text-[#1f2937]">Dashboard</span>
          </div>
          <button 
            onClick={onClose}
            className="w-8 h-8 border-0 bg-transparent rounded-lg cursor-pointer flex items-center justify-center transition-colors hover:bg-black/5"
          >
            <svg viewBox="0 0 24 24" fill="none" className="w-[18px] h-[18px] stroke-[#6b7280]" strokeWidth={2}>
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex px-4 py-2 gap-1 border-b border-[#E8E6DC] bg-[#FAF9F6] shrink-0">
          {['Overview', 'Memory', 'Artifacts'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab.toLowerCase())}
              className={`dashboard-tab ${activeTab === tab.toLowerCase() ? 'active' : ''}`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 dashboard-content">
          {/* Today's Activity Widget */}
          <div className="widget-card">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-semibold text-[#374151] flex items-center gap-2 whitespace-nowrap">
                <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4 stroke-lavender" strokeWidth={2}>
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                </svg>
                Today&apos;s Activity
              </span>
              <span className="widget-badge">Active</span>
            </div>
            <div className="flex gap-3">
              <div className="flex-1 p-4 bg-[#FAF9F6] rounded-lg text-center">
                <div className="text-2xl font-bold text-lavender mb-1">12</div>
                <div className="text-[11px] text-[#6b7280] uppercase tracking-wider font-medium">Messages</div>
              </div>
              <div className="flex-1 p-4 bg-[#FAF9F6] rounded-lg text-center">
                <div className="text-2xl font-bold text-[#1f2937] mb-1">3</div>
                <div className="text-[11px] text-[#6b7280] uppercase tracking-wider font-medium">Tasks</div>
              </div>
              <div className="flex-1 p-4 bg-[#FAF9F6] rounded-lg text-center">
                <div className="text-2xl font-bold text-[#1f2937] mb-1">2</div>
                <div className="text-[11px] text-[#6b7280] uppercase tracking-wider font-medium">Memories</div>
              </div>
            </div>
          </div>

          {/* Memory Confidence Widget */}
          <div className="widget-card">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-semibold text-[#374151] flex items-center gap-2 whitespace-nowrap">
                <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4 stroke-lavender" strokeWidth={2}>
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
                Memory Confidence
              </span>
              <span className="widget-badge info">85%</span>
            </div>
            <div className="progress-bar mb-2">
              <div className="progress-fill" style={{ width: '85%' }}></div>
            </div>
            <div className="flex justify-between text-xs text-[#6b7280]">
              <span>Active Memories: 247</span>
              <span>Archived: 18</span>
            </div>
          </div>

          {/* Recent Files Widget */}
          <div className="widget-card">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-semibold text-[#374151] flex items-center gap-2 whitespace-nowrap">
                <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4 stroke-lavender" strokeWidth={2}>
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14,2 14,8 20,8"/>
                </svg>
                Recent Files
              </span>
            </div>
            <div className="flex flex-col gap-2.5">
              {[
                { name: 'tiger-schema.sql', time: '2m ago', icon: '📄' },
                { name: 'interface-mockup.png', time: '1h ago', icon: '🖼️' },
                { name: 'master-plan.md', time: '3h ago', icon: '📝' },
              ].map((file) => (
                <div key={file.name} className="data-item">
                  <div className="flex items-center gap-2.5 min-w-0 flex-1">
                    <div className="w-7 h-7 rounded-md bg-[#E8E6DC] flex items-center justify-center shrink-0 text-sm">
                      {file.icon}
                    </div>
                    <span className="text-sm font-medium text-[#374151] whitespace-nowrap overflow-hidden text-ellipsis">
                      {file.name}
                    </span>
                  </div>
                  <span className="text-sm font-semibold text-[#1f2937] shrink-0 ml-3">
                    {file.time}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions Widget */}
          <div className="widget-card">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-semibold text-[#374151] flex items-center gap-2 whitespace-nowrap">
                <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4 stroke-lavender" strokeWidth={2}>
                  <polygon points="13,2 3,14 12,14 11,22 21,10 12,10"/>
                </svg>
                Quick Actions
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              {[
                { label: 'New Task', icon: '+' },
                { label: 'Journal', icon: '📔' },
                { label: 'Summary', icon: 'ℹ️' },
                { label: 'Analytics', icon: '📊' },
              ].map((action) => (
                <button key={action.label} className="quick-action">
                  <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-lavender to-lavender-text flex items-center justify-center shrink-0 text-white">
                    {action.icon}
                  </div>
                  <span className="text-[13px] font-medium text-[#374151]">{action.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-[#E8E6DC] bg-[#FAF9F6] shrink-0">
          <div className="text-xs text-[#9ca3af] text-center">
            Last updated: Just now
          </div>
        </div>
      </div>
    </aside>
  );
}
