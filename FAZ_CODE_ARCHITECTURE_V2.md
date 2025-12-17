# FAZ CODE V2 - COMPLETE ARCHITECTURE OVERHAUL

## Executive Summary

The current Faz Code implementation has a fundamental workflow problem: it runs the entire pipeline without user interaction. This document outlines the architectural changes needed to create an **interactive, conversational, transparent** development experience.

---

## CURRENT STATE vs. TARGET STATE

| Aspect | Current | Target |
|--------|---------|--------|
| **Workflow** | Auto-runs all agents | Phase gates with approval |
| **Nicole** | Silent orchestrator | Active collaborator in chat |
| **Research** | Hidden/lost | Visible research.md file |
| **Planning** | Hidden | plan.md + user approval before coding |
| **Coding** | Shows summary only | Streams each file being written |
| **Preview** | Empty/broken | Live updates as files generate |
| **Code Editor** | Read-only Prism | Interactive Monaco with editing |
| **QA** | Score only | Detailed issues list with fix suggestions |
| **Feedback** | None | After each phase, user can provide input |

---

## NEW WORKFLOW

```
USER PROMPT
    ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 1: NICOLE ANALYSIS (Auto)                                  │
│ - Nicole analyzes intent in chat                                 │
│ - Creates PROJECT_BRIEF.md (saved as file)                       │
│ - Asks clarifying questions if needed                            │
│ - Presents understanding back to user                            │
│ → GATE: User confirms understanding                              │
└──────────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 2: RESEARCH (Auto with streaming)                          │
│ - Research Agent searches web/design inspiration                 │
│ - Streams findings to chat in real-time                         │
│ - Creates RESEARCH.md (saved as file)                           │
│ - Shows screenshots of inspiration sites                         │
│ → GATE: User reviews research, provides feedback                 │
└──────────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 3: PLANNING (User approval required)                       │
│ - Planning Agent creates architecture                            │
│ - Creates PLAN.md with:                                         │
│   - Pages to build                                               │
│   - Components needed                                            │
│   - Design tokens (colors, fonts)                               │
│   - File structure                                               │
│ - Nicole presents plan in chat                                   │
│ → GATE: User approves plan or requests changes                   │
└──────────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 4: CODING (Streaming + Live Preview)                       │
│ - Coding Agent generates files ONE BY ONE                        │
│ - Each file streams to chat: "Creating Hero.tsx..."             │
│ - File appears in tree immediately                               │
│ - Preview updates after each critical file                       │
│ - User can pause/intervene if issues seen                        │
│ → Files complete, ready for QA                                   │
└──────────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 5: QA (Transparent)                                        │
│ - QA Agent runs Lighthouse + accessibility                       │
│ - Streams each issue found to chat                              │
│ - Creates QA_REPORT.md with detailed findings                   │
│ - Shows screenshots at different viewports                       │
│ → GATE: User sees issues, decides to fix or accept               │
└──────────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 6: REVIEW (Final check)                                    │
│ - Review Agent performs code review                              │
│ - Creates CODE_REVIEW.md                                        │
│ - Nicole summarizes: "Ready for deployment?"                    │
│ → GATE: User approves for deployment                             │
└──────────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 7: DEPLOY (User triggered)                                 │
│ - User clicks Deploy button                                      │
│ - Creates GitHub repo + Vercel deploy                           │
│ - Shows live URL when complete                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## DATABASE CHANGES

### New Project Status Values

```sql
ALTER TABLE faz_projects 
DROP CONSTRAINT IF EXISTS faz_projects_status_check;

ALTER TABLE faz_projects 
ADD CONSTRAINT faz_projects_status_check CHECK (status IN (
    'intake',           -- Initial state
    'analyzing',        -- Nicole analyzing
    'awaiting_confirm', -- Waiting for user to confirm understanding
    'researching',      -- Research in progress
    'awaiting_research_review', -- User reviewing research
    'planning',         -- Planning in progress
    'awaiting_plan_approval',   -- User must approve plan
    'coding',           -- Code generation
    'qa',               -- QA checks
    'awaiting_qa_review',       -- User reviewing QA issues
    'review',           -- Final review
    'awaiting_deploy_approval', -- User must approve deploy
    'deploying',        -- Deployment in progress
    'deployed',         -- Successfully deployed
    'failed',           -- Pipeline failed
    'paused'            -- User paused
));
```

### Project Artifacts Table

```sql
CREATE TABLE IF NOT EXISTS faz_project_artifacts (
    artifact_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES faz_projects(project_id) ON DELETE CASCADE,
    
    artifact_type VARCHAR(50) NOT NULL, -- 'brief', 'research', 'plan', 'qa_report', 'code_review'
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    
    -- Metadata
    created_by VARCHAR(50), -- agent that created it
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faz_artifacts_project ON faz_project_artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_faz_artifacts_type ON faz_project_artifacts(artifact_type);
```

---

## BACKEND CHANGES

### 1. New Pipeline Mode: Interactive

```python
# backend/app/services/faz_orchestrator.py

class PipelineMode(str, Enum):
    AUTO = "auto"           # Run straight through (current behavior)
    INTERACTIVE = "interactive"  # Stop at gates for user approval

class FazOrchestrator:
    def __init__(self, project_id: int, user_id: int, mode: PipelineMode = PipelineMode.INTERACTIVE):
        self.mode = mode
        # ...
    
    async def run_to_gate(self, gate: str):
        """Run pipeline until a specific gate, then pause for user input."""
        pass
    
    async def proceed_from_gate(self, gate: str, user_input: str = None):
        """User approved gate, continue to next phase."""
        pass
```

### 2. Chat Integration

Nicole must participate in the chat, not just log activities:

```python
# backend/app/services/faz_agents/nicole.py

class NicoleAgent(BaseAgent):
    async def analyze_and_present(self, state: Dict[str, Any]) -> AgentResult:
        """Analyze user request and present understanding in chat."""
        
        # Generate understanding
        understanding = await self._generate_understanding(state["original_prompt"])
        
        # Create PROJECT_BRIEF.md
        brief_content = self._format_brief(understanding)
        
        # Return with chat message for user
        return AgentResult(
            success=True,
            message="I've analyzed your request. Here's my understanding:",
            files={"docs/PROJECT_BRIEF.md": brief_content},
            data={
                "understanding": understanding,
                "questions": self._extract_questions(understanding),
            },
            chat_message=self._format_chat_message(understanding),  # NEW: Direct chat message
            requires_approval=True,  # NEW: Wait for user
        )
```

### 3. File Streaming

Stream each file creation to chat:

```python
# backend/app/services/faz_agents/coding.py

class CodingAgent(BaseAgent):
    async def run(self, state: Dict[str, Any]) -> AgentResult:
        """Generate files with real-time streaming."""
        
        files = {}
        
        # Stream file-by-file instead of all at once
        async for file_path, content in self._generate_files_streaming(state):
            files[file_path] = content
            
            # Broadcast to WebSocket immediately
            await self._broadcast_file_created(file_path, content)
            
            # Send chat message
            await self._send_chat_message(
                f"📝 Created `{file_path}` ({len(content.split(chr(10)))} lines)"
            )
        
        return AgentResult(
            success=True,
            message=f"Generated {len(files)} files",
            files=files,
        )
```

### 4. Research Artifacts

Research agent creates visible artifacts:

```python
# backend/app/services/faz_agents/research.py

class ResearchAgent(BaseAgent):
    async def run(self, state: Dict[str, Any]) -> AgentResult:
        """Research with visible output."""
        
        # Stream research progress to chat
        await self._send_chat_message("🔍 Searching for design inspiration...")
        
        findings = await self._search_web(state["original_prompt"])
        
        # Create RESEARCH.md
        research_md = self._format_research_document(findings)
        
        return AgentResult(
            success=True,
            message="Research complete",
            files={"docs/RESEARCH.md": research_md},
            data={"findings": findings},
            chat_message=self._summarize_findings(findings),
        )
```

---

## FRONTEND CHANGES

### 1. Monaco Editor Integration

Replace Prism with Monaco for full editing:

```tsx
// components/faz/MonacoEditor.tsx
import Editor from '@monaco-editor/react';

export function MonacoEditor({ 
  content, 
  language, 
  path,
  onSave 
}: MonacoEditorProps) {
  const [value, setValue] = useState(content);
  const [isDirty, setIsDirty] = useState(false);
  
  const handleChange = (newValue: string) => {
    setValue(newValue);
    setIsDirty(newValue !== content);
  };
  
  const handleSave = () => {
    onSave(path, value);
    setIsDirty(false);
  };
  
  return (
    <div className="h-full flex flex-col">
      {isDirty && (
        <div className="flex items-center gap-2 px-4 py-2 bg-amber-500/10 border-b border-amber-500/30">
          <span className="text-xs text-amber-400">Unsaved changes</span>
          <button onClick={handleSave} className="text-xs text-amber-400 hover:text-amber-300">
            Save (⌘S)
          </button>
        </div>
      )}
      <Editor
        height="100%"
        language={language}
        value={value}
        onChange={handleChange}
        theme="vs-dark"
        options={{
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
        }}
      />
    </div>
  );
}
```

### 2. Nicole Chat Integration

Chat shows Nicole's messages, not just activity:

```tsx
// components/faz/NicoleChat.tsx

interface Message {
  id: string;
  role: 'user' | 'nicole' | 'agent';
  agent?: string; // For agent messages
  content: string;
  timestamp: string;
  type: 'text' | 'approval_request' | 'file_created' | 'error';
  actions?: { label: string; action: string }[]; // For approval buttons
}

export function NicoleChat({ projectId }: { projectId: number }) {
  const [messages, setMessages] = useState<Message[]>([]);
  
  // ... WebSocket handling to receive messages
  
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
      </div>
      
      {/* Approval buttons when waiting */}
      {waitingForApproval && (
        <div className="p-4 border-t border-[#1e1e2e] bg-[#12121a]">
          <div className="flex gap-2">
            <button 
              onClick={() => handleApproval('approve')}
              className="flex-1 py-2 bg-emerald-600 text-white rounded-lg"
            >
              ✓ Approve & Continue
            </button>
            <button 
              onClick={() => handleApproval('feedback')}
              className="flex-1 py-2 bg-[#1e1e2e] text-white rounded-lg"
            >
              💬 Provide Feedback
            </button>
          </div>
        </div>
      )}
      
      {/* Chat input */}
      <div className="p-4 border-t border-[#1e1e2e]">
        <input 
          type="text" 
          placeholder="Message Nicole..."
          // ...
        />
      </div>
    </div>
  );
}
```

### 3. Live Preview with Auto-Refresh

```tsx
// components/faz/LivePreview.tsx

export function LivePreview({ projectId }: { projectId: number }) {
  const { files } = useFazStore();
  const [previewHtml, setPreviewHtml] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  
  // Rebuild preview when files change
  useEffect(() => {
    if (!autoRefresh) return;
    const html = buildPreviewHtml(files);
    setPreviewHtml(html);
  }, [files, autoRefresh]);
  
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-2 border-b border-[#1e1e2e]">
        <div className="flex gap-1">
          {/* Viewport buttons */}
        </div>
        <label className="flex items-center gap-2 text-xs">
          <input 
            type="checkbox" 
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
          />
          Auto-refresh
        </label>
      </div>
      <div className="flex-1">
        <iframe
          srcDoc={previewHtml}
          className="w-full h-full border-0"
          sandbox="allow-scripts"
        />
      </div>
    </div>
  );
}

function buildPreviewHtml(files: Map<string, string>): string {
  // Get key files
  const layout = files.get('app/layout.tsx') || '';
  const page = files.get('app/page.tsx') || '';
  const globals = files.get('app/globals.css') || '';
  
  // Build components map
  const components: Record<string, string> = {};
  files.forEach((content, path) => {
    if (path.startsWith('components/')) {
      const name = path.split('/').pop()?.replace('.tsx', '') || '';
      components[name] = content;
    }
  });
  
  // Generate preview HTML with Tailwind CDN
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    ${globals.replace(/@import[^;]+;/g, '').replace(/@tailwind[^;]+;/g, '')}
    body { font-family: 'Inter', system-ui, sans-serif; }
  </style>
</head>
<body class="bg-black text-white">
  ${renderReactToHtml(page, components)}
</body>
</html>
  `;
}
```

### 4. File Refresh After Pipeline

```tsx
// Fix: Refresh files when pipeline completes or when viewing project

const fetchProjectData = useCallback(async (projectId: number) => {
  try {
    // Always fetch fresh files from API
    const [filesData, activitiesData, projectData] = await Promise.all([
      fazApi.getFiles(projectId),
      fazApi.getActivities(projectId),
      fazApi.getProject(projectId),
    ]);
    
    // Update store with fresh data
    setFiles(filesData || []);
    setActivities(activitiesData || []);
    setCurrentProject(projectData);
    
    console.log(`[Faz] Loaded ${filesData?.length || 0} files for project ${projectId}`);
    
    // Auto-select first file
    if (filesData && filesData.length > 0) {
      const preferred = filesData.find(f => f.path.includes('page.tsx')) || filesData[0];
      openFile(preferred);
    }
  } catch (error) {
    console.error('Failed to fetch project data:', error);
  }
}, []);

// Poll for updates while pipeline is running
useEffect(() => {
  if (!pipelineRunning || !currentProject) return;
  
  const interval = setInterval(() => {
    fetchProjectData(currentProject.project_id);
  }, 3000); // Refresh every 3s while running
  
  return () => clearInterval(interval);
}, [pipelineRunning, currentProject, fetchProjectData]);
```

---

## IMPLEMENTATION ORDER

### Phase 1: Fix Immediate Issues (Day 1)
1. ✅ Fix file loading - ensure files populate in store
2. ✅ Fix preview - render actual generated HTML
3. ✅ Add file polling while pipeline runs

### Phase 2: Add Monaco Editor (Day 2)
1. Install `@monaco-editor/react`
2. Replace Prism viewer with Monaco
3. Add save functionality
4. Add keyboard shortcuts (Cmd+S)

### Phase 3: Interactive Pipeline (Days 3-4)
1. Add approval gates to orchestrator
2. Add Nicole chat messages (not just activities)
3. Create PROJECT_BRIEF.md, RESEARCH.md, PLAN.md artifacts
4. Implement "Approve & Continue" / "Provide Feedback" UI

### Phase 4: Streaming (Day 5)
1. Stream file creation to chat
2. Stream agent thinking to chat
3. Live file tree updates via WebSocket

### Phase 5: QA Transparency (Day 6)
1. Create QA_REPORT.md with issues
2. Display issues in UI with fix suggestions
3. Allow user to request fixes

### Phase 6: Polish (Day 7)
1. Full preview with Tailwind rendering
2. Deploy integration
3. Error handling and edge cases

---

## SUCCESS CRITERIA

After implementation, user should be able to:

1. ✅ See Nicole's analysis in chat and confirm understanding
2. ✅ Review research.md before planning starts
3. ✅ Approve the plan.md before coding begins
4. ✅ Watch files being created in real-time
5. ✅ See preview update as each component is added
6. ✅ Edit any file directly in Monaco
7. ✅ See QA issues with specific details
8. ✅ Provide feedback at any phase
9. ✅ Deploy when satisfied

---

## NEXT STEPS

1. **Immediate**: Fix file loading issue
2. **Today**: Add Monaco editor
3. **Tomorrow**: Implement approval gates
4. **This week**: Full interactive pipeline

