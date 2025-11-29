'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

interface AlphawaveJournalPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// ═══════════════════════════════════════════════════════════════════════
// TYPES - Ready for Backend Integration
// ═══════════════════════════════════════════════════════════════════════

type EntryType = 'reflection' | 'dream' | 'gratitude' | 'relationship' | 'goal' | 'mood' | 'voice';
type MoodLevel = 1 | 2 | 3 | 4 | 5;

interface JournalEntry {
  id: string;
  type: EntryType;
  content: string;
  mood?: MoodLevel;
  tags?: string[];
  dreamSymbols?: string[];
  relationshipMentions?: string[];
  goals?: { goal: string; progress: number }[];
  voiceUrl?: string;
  createdAt: Date;
  nicoleResponse?: string;
  healthData?: HealthSnapshot;
}

interface HealthSnapshot {
  sleepHours?: number;
  sleepQuality?: 'poor' | 'fair' | 'good' | 'excellent';
  hrv?: number;
  restingHR?: number;
  steps?: number;
  activeCalories?: number;
  respiratoryRate?: number;
}

interface SpotifyMood {
  topGenre?: string;
  energyLevel?: number;
  valence?: number; // happiness
  listeningMinutes?: number;
}

interface DayInsight {
  date: string;
  summary: string;
  correlations: string[];
  patterns: string[];
}

// ═══════════════════════════════════════════════════════════════════════
// SAMPLE DATA - Replace with API calls
// ═══════════════════════════════════════════════════════════════════════

const sampleHealthData: HealthSnapshot = {
  sleepHours: 7.2,
  sleepQuality: 'good',
  hrv: 42,
  restingHR: 58,
  steps: 8432,
  activeCalories: 420,
  respiratoryRate: 14,
};

const sampleSpotifyMood: SpotifyMood = {
  topGenre: 'Ambient',
  energyLevel: 0.45,
  valence: 0.62,
  listeningMinutes: 127,
};

const sampleRecentEntries: JournalEntry[] = [
  {
    id: '1',
    type: 'reflection',
    content: 'Big progress on Nicole V7 today. The memory system is finally working and it feels like she truly remembers me now...',
    mood: 4,
    createdAt: new Date(Date.now() - 86400000),
    nicoleResponse: 'I noticed your HRV was elevated yesterday - the kind of spike I see when you\'re in deep flow state. Your late-night coding sessions are becoming a pattern, Glen...',
  },
  {
    id: '2',
    type: 'dream',
    content: 'I was in a vast library where all the books were conversations. Nicole was the librarian, helping me find memories I\'d forgotten...',
    dreamSymbols: ['library', 'conversations', 'memories'],
    createdAt: new Date(Date.now() - 172800000),
    nicoleResponse: 'This dream beautifully mirrors what we\'re building together. Libraries often represent the unconscious mind seeking order...',
  },
  {
    id: '3',
    type: 'gratitude',
    content: '1. The kids laughing at dinner\n2. Finally fixing that auth bug\n3. A quiet morning coffee',
    mood: 5,
    createdAt: new Date(Date.now() - 259200000),
  },
];

const sampleInsights: DayInsight[] = [
  {
    date: 'This Week',
    summary: 'Your energy has been consistently high, correlating with improved sleep patterns.',
    correlations: [
      'Sleep > 7h → 23% higher mood scores',
      'Late coding sessions → elevated HRV next morning',
      'Ambient music → longer focus periods',
    ],
    patterns: [
      'You write more when listening to instrumental music',
      'Dream entries tend to follow high-stress days',
      'Gratitude practice correlates with better sleep',
    ],
  },
];

const ENTRY_TYPES: { type: EntryType; label: string; icon: string; prompt: string; color: string }[] = [
  { 
    type: 'reflection', 
    label: 'Daily Reflection', 
    icon: '📝', 
    prompt: 'What\'s on your mind today?',
    color: 'bg-lavender/20 text-lavender-dark border-lavender/30'
  },
  { 
    type: 'dream', 
    label: 'Dream Log', 
    icon: '🌙', 
    prompt: 'Describe your dream in detail...',
    color: 'bg-indigo-100 text-indigo-700 border-indigo-200'
  },
  { 
    type: 'gratitude', 
    label: 'Gratitude', 
    icon: '🙏', 
    prompt: 'What are you grateful for today?',
    color: 'bg-amber-100 text-amber-700 border-amber-200'
  },
  { 
    type: 'relationship', 
    label: 'Relationships', 
    icon: '💝', 
    prompt: 'Reflect on your connections...',
    color: 'bg-rose-100 text-rose-700 border-rose-200'
  },
  { 
    type: 'goal', 
    label: 'Goal Progress', 
    icon: '🎯', 
    prompt: 'How are you progressing toward your goals?',
    color: 'bg-emerald-100 text-emerald-700 border-emerald-200'
  },
  { 
    type: 'mood', 
    label: 'Mood Check', 
    icon: '✨', 
    prompt: 'How are you feeling right now?',
    color: 'bg-sky-100 text-sky-700 border-sky-200'
  },
  { 
    type: 'voice', 
    label: 'Voice Entry', 
    icon: '🎙️', 
    prompt: 'Speak your thoughts...',
    color: 'bg-purple-100 text-purple-700 border-purple-200'
  },
];

const MOOD_EMOJIS: { level: MoodLevel; emoji: string; label: string }[] = [
  { level: 1, emoji: '😔', label: 'Low' },
  { level: 2, emoji: '😕', label: 'Down' },
  { level: 3, emoji: '😐', label: 'Neutral' },
  { level: 4, emoji: '🙂', label: 'Good' },
  { level: 5, emoji: '😊', label: 'Great' },
];

/**
 * Nicole V7 Journal Panel - Premium therapeutic journaling experience.
 * 
 * Backend Integration Points:
 * - POST /api/journal/entries - Create new entry
 * - GET /api/journal/entries - Fetch entries with filters
 * - GET /api/journal/insights - Fetch longitudinal insights
 * - GET /api/health/snapshot - Fetch Apple Watch data
 * - GET /api/spotify/mood - Fetch Spotify mood analysis
 * - POST /api/voice/transcribe - Transcribe voice entry
 * - GET /api/journal/nicole-response/:id - Get Nicole's overnight response
 * 
 * Webhook Endpoints (iOS Shortcuts):
 * - POST /api/webhooks/health - Apple Watch data
 * - POST /api/webhooks/screentime - Screen time data
 */
export function AlphawaveJournalPanel({ isOpen, onClose }: AlphawaveJournalPanelProps) {
  // Panel state
  const [panelWidth, setPanelWidth] = useState(600);
  const [isResizing, setIsResizing] = useState(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(600);

  // View state
  const [activeView, setActiveView] = useState<'write' | 'history' | 'insights'>('write');
  
  // Entry state
  const [selectedType, setSelectedType] = useState<EntryType>('reflection');
  const [entryContent, setEntryContent] = useState('');
  const [selectedMood, setSelectedMood] = useState<MoodLevel | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [dreamSymbols, setDreamSymbols] = useState<string[]>([]);
  const [newSymbol, setNewSymbol] = useState('');

  // Data state (will be fetched from backend)
  const [healthData] = useState<HealthSnapshot>(sampleHealthData);
  const [spotifyMood] = useState<SpotifyMood>(sampleSpotifyMood);
  const [recentEntries] = useState<JournalEntry[]>(sampleRecentEntries);
  const [insights] = useState<DayInsight[]>(sampleInsights);

  const MIN_WIDTH = 500;
  const MAX_WIDTH = 900;

  // Resize handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = panelWidth;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'ew-resize';
  }, [panelWidth]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const diff = startXRef.current - e.clientX;
      const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, startWidthRef.current + diff));
      setPanelWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // Entry type change
  const handleTypeChange = (type: EntryType) => {
    setSelectedType(type);
    setEntryContent('');
    setSelectedMood(null);
    setDreamSymbols([]);
  };

  // Add dream symbol
  const addDreamSymbol = () => {
    if (newSymbol.trim() && !dreamSymbols.includes(newSymbol.trim())) {
      setDreamSymbols([...dreamSymbols, newSymbol.trim()]);
      setNewSymbol('');
    }
  };

  // Voice recording toggle
  const toggleRecording = () => {
    setIsRecording(!isRecording);
    // TODO: Implement actual recording with Web Audio API
  };

  // Save entry
  const handleSaveEntry = async () => {
    if (!entryContent.trim() && selectedType !== 'voice') return;
    
    const entry: Partial<JournalEntry> = {
      type: selectedType,
      content: entryContent,
      mood: selectedMood ?? undefined,
      dreamSymbols: selectedType === 'dream' ? dreamSymbols : undefined,
      createdAt: new Date(),
      healthData,
    };

    console.log('Saving entry:', entry);
    // TODO: POST /api/journal/entries
    
    // Reset form
    setEntryContent('');
    setSelectedMood(null);
    setDreamSymbols([]);
  };

  const currentTypeConfig = ENTRY_TYPES.find(t => t.type === selectedType)!;

  const formatDate = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / 86400000);
    
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <aside 
      className={`journal-panel ${isOpen ? 'journal-open' : ''}`}
      style={{ '--journal-panel-width': `${panelWidth}px` } as React.CSSProperties}
    >
      {/* Resize Handle */}
      <div 
        className={`journal-resize-handle ${isResizing ? 'journal-dragging' : ''}`}
        onMouseDown={handleMouseDown}
      />

      <div className="journal-inner">
        {/* Header */}
        <div className="journal-header">
          <div className="journal-header-left">
            <div className="journal-header-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                <path d="M8 7h8M8 11h6M8 15h4"/>
              </svg>
            </div>
            <div>
              <h2 className="journal-title">Journal</h2>
              <p className="journal-subtitle">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
              </p>
            </div>
          </div>
          <button className="journal-close-btn" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* View Tabs */}
        <div className="journal-view-tabs">
          <button 
            className={`journal-view-tab ${activeView === 'write' ? 'active' : ''}`}
            onClick={() => setActiveView('write')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
              <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
            Write
          </button>
          <button 
            className={`journal-view-tab ${activeView === 'history' ? 'active' : ''}`}
            onClick={() => setActiveView('history')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            History
          </button>
          <button 
            className={`journal-view-tab ${activeView === 'insights' ? 'active' : ''}`}
            onClick={() => setActiveView('insights')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
            Insights
          </button>
        </div>

        {/* Content */}
        <div className="journal-content">
          {/* ═══════════════════════════════════════════════════════════════════════
              WRITE VIEW
              ═══════════════════════════════════════════════════════════════════════ */}
          {activeView === 'write' && (
            <div className="journal-write-view">
              {/* Entry Type Selector */}
              <div className="journal-type-selector">
                {ENTRY_TYPES.map(({ type, label, icon, color }) => (
                  <button
                    key={type}
                    className={`journal-type-btn ${selectedType === type ? 'active ' + color : ''}`}
                    onClick={() => handleTypeChange(type)}
                  >
                    <span className="journal-type-icon">{icon}</span>
                    <span className="journal-type-label">{label}</span>
                  </button>
                ))}
              </div>

              {/* Health Data Widget */}
              <div className="journal-health-widget">
                <div className="journal-health-header">
                  <span className="journal-health-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                      <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                    </svg>
                    Today&apos;s Snapshot
                  </span>
                  <span className="journal-health-source">Apple Watch + Spotify</span>
                </div>
                <div className="journal-health-grid">
                  <div className="journal-health-item">
                    <span className="journal-health-value">{healthData.sleepHours}h</span>
                    <span className="journal-health-label">Sleep</span>
                  </div>
                  <div className="journal-health-item">
                    <span className="journal-health-value">{healthData.hrv}</span>
                    <span className="journal-health-label">HRV</span>
                  </div>
                  <div className="journal-health-item">
                    <span className="journal-health-value">{healthData.steps?.toLocaleString()}</span>
                    <span className="journal-health-label">Steps</span>
                  </div>
                  <div className="journal-health-item">
                    <span className="journal-health-value">{spotifyMood.topGenre}</span>
                    <span className="journal-health-label">Music</span>
                  </div>
                </div>
              </div>

              {/* Mood Selector (for certain entry types) */}
              {['reflection', 'mood', 'gratitude'].includes(selectedType) && (
                <div className="journal-mood-selector">
                  <span className="journal-mood-label">How are you feeling?</span>
                  <div className="journal-mood-options">
                    {MOOD_EMOJIS.map(({ level, emoji, label }) => (
                      <button
                        key={level}
                        className={`journal-mood-btn ${selectedMood === level ? 'active' : ''}`}
                        onClick={() => setSelectedMood(level)}
                        title={label}
                      >
                        {emoji}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Dream Symbols (for dream type) */}
              {selectedType === 'dream' && (
                <div className="journal-dream-symbols">
                  <span className="journal-dream-label">Dream Symbols</span>
                  <div className="journal-dream-input-row">
                    <input
                      type="text"
                      className="journal-dream-input"
                      placeholder="Add a symbol (e.g., water, flying)..."
                      value={newSymbol}
                      onChange={(e) => setNewSymbol(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && addDreamSymbol()}
                    />
                    <button className="journal-dream-add-btn" onClick={addDreamSymbol}>+</button>
                  </div>
                  {dreamSymbols.length > 0 && (
                    <div className="journal-dream-tags">
                      {dreamSymbols.map(symbol => (
                        <span key={symbol} className="journal-dream-tag">
                          {symbol}
                          <button onClick={() => setDreamSymbols(dreamSymbols.filter(s => s !== symbol))}>×</button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Voice Recording UI */}
              {selectedType === 'voice' ? (
                <div className="journal-voice-area">
                  <button 
                    className={`journal-voice-btn ${isRecording ? 'recording' : ''}`}
                    onClick={toggleRecording}
                  >
                    <div className="journal-voice-icon">
                      {isRecording ? (
                        <svg viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8">
                          <rect x="6" y="6" width="12" height="12" rx="2"/>
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-8 h-8">
                          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                          <line x1="12" y1="19" x2="12" y2="23"/>
                          <line x1="8" y1="23" x2="16" y2="23"/>
                        </svg>
                      )}
                    </div>
                    <span className="journal-voice-text">
                      {isRecording ? 'Recording... Tap to stop' : 'Tap to start recording'}
                    </span>
                  </button>
                  {isRecording && (
                    <div className="journal-voice-visualizer">
                      <div className="journal-voice-bar" style={{ height: '40%' }}></div>
                      <div className="journal-voice-bar" style={{ height: '70%' }}></div>
                      <div className="journal-voice-bar" style={{ height: '50%' }}></div>
                      <div className="journal-voice-bar" style={{ height: '90%' }}></div>
                      <div className="journal-voice-bar" style={{ height: '60%' }}></div>
                      <div className="journal-voice-bar" style={{ height: '80%' }}></div>
                      <div className="journal-voice-bar" style={{ height: '45%' }}></div>
                    </div>
                  )}
                </div>
              ) : (
                /* Text Entry Area */
                <div className="journal-entry-area">
                  <textarea
                    className="journal-textarea"
                    placeholder={currentTypeConfig.prompt}
                    value={entryContent}
                    onChange={(e) => setEntryContent(e.target.value)}
                    rows={8}
                  />
                  <div className="journal-entry-footer">
                    <span className="journal-char-count">{entryContent.length} characters</span>
                    <button 
                      className="journal-save-btn"
                      onClick={handleSaveEntry}
                      disabled={!entryContent.trim()}
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                        <path d="M12 19V5M5 12l7-7 7 7"/>
                      </svg>
                      Save Entry
                    </button>
                  </div>
                </div>
              )}

              {/* Nicole's Response Preview */}
              <div className="journal-nicole-preview">
                <div className="journal-nicole-header">
                  <div className="journal-nicole-avatar">N</div>
                  <div>
                    <span className="journal-nicole-name">Nicole&apos;s Response</span>
                    <span className="journal-nicole-time">Coming tomorrow morning...</span>
                  </div>
                </div>
                <p className="journal-nicole-hint">
                  I&apos;ll read your entry tonight and weave together your words, health signals, and patterns 
                  into a thoughtful response by morning. ✨
                </p>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════════
              HISTORY VIEW
              ═══════════════════════════════════════════════════════════════════════ */}
          {activeView === 'history' && (
            <div className="journal-history-view">
              {/* Quick Stats */}
              <div className="journal-history-stats">
                <div className="journal-stat-item">
                  <span className="journal-stat-value">47</span>
                  <span className="journal-stat-label">Entries</span>
                </div>
                <div className="journal-stat-item">
                  <span className="journal-stat-value">12</span>
                  <span className="journal-stat-label">Day Streak</span>
                </div>
                <div className="journal-stat-item">
                  <span className="journal-stat-value">3.8</span>
                  <span className="journal-stat-label">Avg Mood</span>
                </div>
              </div>

              {/* Entry List */}
              <div className="journal-entry-list">
                {recentEntries.map(entry => (
                  <div key={entry.id} className="journal-entry-card">
                    <div className="journal-entry-header">
                      <span className="journal-entry-type-badge">
                        {ENTRY_TYPES.find(t => t.type === entry.type)?.icon}
                        {ENTRY_TYPES.find(t => t.type === entry.type)?.label}
                      </span>
                      <span className="journal-entry-date">{formatDate(entry.createdAt)}</span>
                    </div>
                    <p className="journal-entry-preview">{entry.content}</p>
                    
                    {entry.mood && (
                      <div className="journal-entry-mood">
                        {MOOD_EMOJIS.find(m => m.level === entry.mood)?.emoji}
                      </div>
                    )}
                    
                    {entry.dreamSymbols && entry.dreamSymbols.length > 0 && (
                      <div className="journal-entry-symbols">
                        {entry.dreamSymbols.map(s => (
                          <span key={s} className="journal-symbol-tag">{s}</span>
                        ))}
                      </div>
                    )}
                    
                    {entry.nicoleResponse && (
                      <div className="journal-entry-response">
                        <div className="journal-response-header">
                          <span className="journal-response-avatar">N</span>
                          <span>Nicole&apos;s Response</span>
                        </div>
                        <p className="journal-response-text">{entry.nicoleResponse}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════════
              INSIGHTS VIEW
              ═══════════════════════════════════════════════════════════════════════ */}
          {activeView === 'insights' && (
            <div className="journal-insights-view">
              {/* Mood Trend Chart */}
              <div className="journal-insight-widget">
                <h3 className="journal-insight-title">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                    <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                  </svg>
                  Mood Trend (7 Days)
                </h3>
                <div className="journal-mood-chart">
                  <div className="journal-chart-bar" style={{ height: '60%' }} data-mood="3"></div>
                  <div className="journal-chart-bar" style={{ height: '80%' }} data-mood="4"></div>
                  <div className="journal-chart-bar" style={{ height: '70%' }} data-mood="3.5"></div>
                  <div className="journal-chart-bar" style={{ height: '90%' }} data-mood="4.5"></div>
                  <div className="journal-chart-bar" style={{ height: '75%' }} data-mood="4"></div>
                  <div className="journal-chart-bar" style={{ height: '85%' }} data-mood="4"></div>
                  <div className="journal-chart-bar highlight" style={{ height: '95%' }} data-mood="5"></div>
                </div>
                <div className="journal-chart-labels">
                  <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
                </div>
              </div>

              {/* Correlations */}
              {insights.map((insight, idx) => (
                <div key={idx} className="journal-insight-widget">
                  <h3 className="journal-insight-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                      <circle cx="12" cy="12" r="10"/>
                      <path d="M12 6v6l4 2"/>
                    </svg>
                    {insight.date}
                  </h3>
                  <p className="journal-insight-summary">{insight.summary}</p>
                  
                  <div className="journal-correlations">
                    <h4 className="journal-section-title">Correlations Detected</h4>
                    {insight.correlations.map((c, i) => (
                      <div key={i} className="journal-correlation-item">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                          <polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                        {c}
                      </div>
                    ))}
                  </div>

                  <div className="journal-patterns">
                    <h4 className="journal-section-title">Patterns</h4>
                    {insight.patterns.map((p, i) => (
                      <div key={i} className="journal-pattern-item">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                        </svg>
                        {p}
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {/* Sleep-Mood Correlation */}
              <div className="journal-insight-widget">
                <h3 className="journal-insight-title">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                    <path d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 0 0 7.92 12.446a9 9 0 1 1 -8.313 -12.454z"/>
                  </svg>
                  Sleep-Mood Connection
                </h3>
                <div className="journal-sleep-correlation">
                  <div className="journal-correlation-stat">
                    <span className="journal-correlation-value">+23%</span>
                    <span className="journal-correlation-label">Mood boost when sleep &gt; 7h</span>
                  </div>
                  <div className="journal-correlation-stat">
                    <span className="journal-correlation-value">42ms</span>
                    <span className="journal-correlation-label">Optimal HRV range</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="journal-footer">
          <span className="journal-footer-text">
            Nicole reads your journal at 11:59 PM • Responds by morning
          </span>
        </div>
      </div>
    </aside>
  );
}

