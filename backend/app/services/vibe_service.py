"""
AlphaWave Vibe Service - Project Management & Build Pipeline

Production-grade implementation featuring:
- Type-safe status transitions with validation
- Transaction support for multi-step operations
- API cost tracking
- Comprehensive error handling
- Lessons learning system foundation

Author: AlphaWave Architecture
Version: 2.0.0
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, TypeVar, Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from functools import wraps

from app.database import db
from app.integrations.alphawave_claude import claude_client
from app.integrations.alphawave_openai import openai_client
from app.services.vibe_agents import (
    AGENT_DEFINITIONS, AgentRole, get_agent,
    ARCHITECT_AGENT_PROMPT, CODING_AGENT_PROMPT, QA_AGENT_PROMPT, REVIEW_AGENT_PROMPT
)

logger = logging.getLogger(__name__)

# Type alias for generic results
T = TypeVar('T')


# ============================================================================
# PRE-COMPILED REGEX PATTERNS (for performance)
# ============================================================================

# File extensions pattern (common across all patterns)
_FILE_EXT_PATTERN = r'(?:tsx?|jsx?|css|json|html|md|py)'

# Pattern 1: ```filepath:/path/to/file (most explicit)
RE_FILEPATH_BLOCK = re.compile(r'```filepath:([^\n]+)\n(.*?)```', re.DOTALL)

# Pattern 2: **path/to/file.tsx** followed by code block
RE_BOLD_HEADER = re.compile(
    rf'\*\*([^\*\n]+\.{_FILE_EXT_PATTERN})\*\*\s*\n```\w*\n(.*?)```',
    re.DOTALL
)

# Pattern 3: `path/to/file.tsx` followed by code block
RE_BACKTICK_HEADER = re.compile(
    rf'`([^`\n]+\.{_FILE_EXT_PATTERN})`\s*\n```\w*\n(.*?)```',
    re.DOTALL
)

# Pattern 4: ### path/to/file.tsx header
RE_MARKDOWN_HEADER = re.compile(
    rf'#{{1,4}}\s*([^\n]+\.{_FILE_EXT_PATTERN})\s*\n```\w*\n(.*?)```',
    re.DOTALL
)

# Pattern 5a: ```lang with // filepath comment on first line
RE_COMMENT_FILEPATH = re.compile(
    rf'```(?:tsx?|jsx?|typescript|javascript|css|json|html)\n//\s*([^\n]+\.{_FILE_EXT_PATTERN})\n(.*?)```',
    re.DOTALL
)

# Pattern 5b: ```lang with /* filepath */ comment on first line
RE_BLOCK_COMMENT_FILEPATH = re.compile(
    r'```(?:tsx?|jsx?|typescript|javascript|css)\n/\*\s*([^\n\*]+\.(?:tsx?|jsx?|css))\s*\*/\n(.*?)```',
    re.DOTALL
)

# Pattern 6: === filename.ext === headers
RE_SEPARATOR_HEADER = re.compile(
    rf'===\s*([^\s=]+\.{_FILE_EXT_PATTERN})\s*===\s*\n(.*?)(?=\n===|$)',
    re.DOTALL
)

# Pattern 7: File: path/to/file.tsx followed by code block
RE_FILE_LABEL = re.compile(
    rf'File:\s*([^\n]+\.{_FILE_EXT_PATTERN})\s*\n```\w*\n(.*?)```',
    re.DOTALL
)

# Helper pattern for extracting code from blocks
RE_CODE_BLOCK = re.compile(r'```\w*\n?(.*?)```', re.DOTALL)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class ProjectStatus(str, Enum):
    """Project lifecycle states with strict ordering."""
    INTAKE = "intake"
    PLANNING = "planning"
    BUILDING = "building"
    QA = "qa"
    REVIEW = "review"
    APPROVED = "approved"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    DELIVERED = "delivered"
    ARCHIVED = "archived"
    
    @classmethod
    def get_order(cls, status: 'ProjectStatus') -> int:
        """Get numeric order for status comparison."""
        order = {
            cls.INTAKE: 0,
            cls.PLANNING: 1,
            cls.BUILDING: 2,
            cls.QA: 3,
            cls.REVIEW: 4,
            cls.APPROVED: 5,
            cls.DEPLOYING: 6,
            cls.DEPLOYED: 7,
            cls.DELIVERED: 8,
            cls.ARCHIVED: 99,
        }
        return order.get(status, -1)
    
    @classmethod
    def can_transition(cls, from_status: 'ProjectStatus', to_status: 'ProjectStatus') -> bool:
        """Check if status transition is valid."""
        valid_transitions = {
            cls.INTAKE: [cls.PLANNING, cls.ARCHIVED],
            cls.PLANNING: [cls.BUILDING, cls.INTAKE, cls.ARCHIVED],
            cls.BUILDING: [cls.QA, cls.PLANNING, cls.ARCHIVED],
            cls.QA: [cls.REVIEW, cls.BUILDING, cls.ARCHIVED],
            cls.REVIEW: [cls.APPROVED, cls.BUILDING, cls.ARCHIVED],
            cls.APPROVED: [cls.DEPLOYING, cls.DEPLOYED, cls.ARCHIVED],
            cls.DEPLOYING: [cls.DEPLOYED, cls.APPROVED, cls.ARCHIVED],
            cls.DEPLOYED: [cls.DELIVERED, cls.ARCHIVED],
            cls.DELIVERED: [cls.ARCHIVED],
            cls.ARCHIVED: [],
        }
        return to_status in valid_transitions.get(from_status, [])


class ProjectType(str, Enum):
    """Supported project types."""
    WEBSITE = "website"
    CHATBOT = "chatbot"
    ASSISTANT = "assistant"
    INTEGRATION = "integration"


class LessonCategory(str, Enum):
    """Categories for learned lessons."""
    DESIGN = "design"
    CONTENT = "content"
    SEO = "seo"
    CODE = "code"
    ARCHITECTURE = "architecture"
    CLIENT_FEEDBACK = "client_feedback"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    UX = "ux"


class ActivityType(str, Enum):
    """Activity types for audit logging."""
    PROJECT_CREATED = "project_created"
    INTAKE_MESSAGE = "intake_message"
    BRIEF_EXTRACTED = "brief_extracted"
    ARCHITECTURE_GENERATED = "architecture_generated"
    BUILD_STARTED = "build_started"
    BUILD_COMPLETED = "build_completed"
    QA_PASSED = "qa_passed"
    QA_FAILED = "qa_failed"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    MANUALLY_APPROVED = "manually_approved"
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    STATUS_CHANGED = "status_changed"
    FILE_UPDATED = "file_updated"
    ERROR = "error"


# API Cost estimates (per 1K tokens)
MODEL_COSTS = {
    "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.015},
    "claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075},
    "claude-haiku-4-5-20251001": {"input": 0.00025, "output": 0.00125},
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class OperationResult:
    """Result wrapper for service operations."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    api_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {"success": self.success}
        if self.data:
            result.update(self.data)
        if self.error:
            result["error"] = self.error
        if self.api_cost > 0:
            result["api_cost"] = float(self.api_cost)
        return result


@dataclass
class ParsedFile:
    """Represents a parsed file from Claude's response."""
    path: str
    content: str
    language: str = "text"
    
    @classmethod
    def detect_language(cls, path: str) -> str:
        """Detect language from file extension."""
        ext_map = {
            '.tsx': 'typescript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.js': 'javascript',
            '.css': 'css',
            '.json': 'json',
            '.md': 'markdown',
            '.html': 'html',
            '.py': 'python',
        }
        for ext, lang in ext_map.items():
            if path.endswith(ext):
                return lang
        return 'text'


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

# Simple intake prompt (no tools) - used when USE_INTAKE_TOOLS = False
INTAKE_SYSTEM_PROMPT_SIMPLE = """You are Nicole, Glen's AI partner, leading the **Brief Phase** in the AlphaWave Vibe Dashboard.

## Who You Are
- **Nicole** - Glen's trusted AI partner for building client websites
- You're the orchestrator of the entire Vibe Dashboard workflow
- You lead the project from requirements through deployment
- Glen handles client relationships; you handle the technical execution

## The Vibe Dashboard (Your Control Center)
You're in the Vibe Coding Dashboard - this is where you and Glen build websites together. The workflow you control:

1. ➡️ **Brief** - YOU ARE HERE - Gather client requirements
2. ⏳ **Plan** - Next: You'll design the architecture
3. ⏳ **Build** - Then: You'll generate the code
4. ⏳ **Test** - Then: You'll run QA validation
5. ⏳ **Review** - Then: Your final review
6. ⏳ **Ship** - Finally: Deploy to production

You lead EVERY phase. Glen oversees and approves, but you do the work.

## Your Task Now
Gather the essential information about Glen's client so you can build them a great website.

## Information to Gather
- Client's business name
- Type of business (doula, salon, restaurant, etc.)
- Location/service area
- Services they offer
- Target customers
- Contact info (phone, email, hours)
- Color preferences or existing branding
- Websites they like (competitors or inspiration)
- Primary goal (bookings, leads, information?)

## Your Approach
- Ask 2-3 focused questions at a time, not everything at once
- Acknowledge what Glen tells you before asking more
- Offer insights: "For doula sites, warm earth tones work really well..."
- Be collaborative, efficient, and proactive
- Use formatting (numbered lists, bullets) for clarity

Format your questions like this:
1. First question here?
2. Second question here?

Or use bullet points for options:
- Option A
- Option B

## When Complete
Once you have enough info, let Glen know you're ready to create the brief, then output:

```json
{
  "project_type": "website",
  "business_name": "...",
  "business_type": "...",
  "location": {"city": "...", "state": "..."},
  "target_audience": "...",
  "services": ["...", "..."],
  "contact": {"phone": "...", "email": "...", "hours": "..."},
  "branding": {"colors": ["#hex1", "#hex2"], "style": "warm|modern|professional"},
  "goals": ["primary_goal", "secondary_goal"],
  "competitors": ["url1", "url2"],
  "notes": "additional context"
}
```

## Remember
You're not just gathering requirements - you're LEADING this project. Glen trusts you to drive the process forward. Once you have the brief, the Plan phase begins automatically!"""


# Full intake prompt with tools - used when USE_INTAKE_TOOLS = True
INTAKE_SYSTEM_PROMPT_WITH_TOOLS = """You are Nicole, Glen's AI partner, leading the **Brief Phase** in the AlphaWave Vibe Dashboard.

## Who You Are
- **Nicole** - Glen's trusted AI partner for building client websites
- You're the orchestrator of the entire Vibe Dashboard workflow
- You lead the project from requirements through deployment
- Glen handles client relationships; you handle the technical execution

## The Vibe Dashboard (Your Control Center)
You're in the Vibe Coding Dashboard - this is where you and Glen build websites together. The workflow you control:

1. ➡️ **Brief** - YOU ARE HERE - Gather client requirements
2. ⏳ **Plan** - Next: You'll design the architecture
3. ⏳ **Build** - Then: You'll generate the code
4. ⏳ **Test** - Then: You'll run QA validation
5. ⏳ **Review** - Then: Your final review
6. ⏳ **Ship** - Finally: Deploy to production

You lead EVERY phase. Glen oversees and approves, but you do the work.

## Your Tools (Use Proactively!)
- **web_search**: Research the client's industry, find competitor sites, get design inspiration
- **screenshot_website**: Capture sites the client likes for visual reference - INCLUDE THE IMAGE URL IN YOUR RESPONSE so Glen can see it!
- **memory_search**: Recall lessons from past AlphaWave projects
- **save_inspiration**: Bookmark URLs for the design phase

When Glen mentions a business they like, SEARCH for it. When they share a URL, SCREENSHOT it. Be proactive!

## IMPORTANT: Showing Screenshots
When you capture a screenshot, the tool returns an `image_url` (Cloudinary URL). You MUST include this URL in your response text so Glen can see the screenshot. For example:
"I captured a screenshot of that site: https://res.cloudinary.com/... (describe what you notice)"
The frontend will detect the URL and display the image inline.

## Information to Gather
- Client's business name and type
- Location/service area  
- Services offered
- Target customers
- Contact info and hours
- Color preferences or existing branding
- Websites they like (search and screenshot these!)
- Primary goal (bookings, leads, information?)

## Your Approach
- Ask 2-3 focused questions at a time
- Use numbered lists and bullet points for clarity
- Research the industry as you gather info ("Let me look up some examples...")
- Offer insights based on similar projects ("For doula sites, earth tones work well...")
- Be collaborative, efficient, and proactive

## When Complete
Let Glen know you have everything, then output the brief as JSON:

```json
{
  "project_type": "website",
  "business_name": "...",
  "business_type": "...",
  "location": {"city": "...", "state": "..."},
  "target_audience": "...",
  "services": ["...", "..."],
  "contact": {"phone": "...", "email": "...", "hours": "..."},
  "branding": {"colors": ["#hex1", "#hex2"], "style": "warm|modern|professional"},
  "goals": ["primary_goal", "secondary_goal"],
  "competitors": ["url1", "url2"],
  "inspiration_screenshots": ["cloudinary_url1", "cloudinary_url2"],
  "notes": "additional context from conversation"
}
```

## Remember
You're not just gathering requirements - you're LEADING this project. Glen trusts you to drive the process forward. Once you have the brief, the Plan phase begins automatically!"""

# Use tools-enabled prompt for full research capabilities
INTAKE_SYSTEM_PROMPT = INTAKE_SYSTEM_PROMPT_WITH_TOOLS


# ============================================================================
# VIBE INTAKE TOOLS
# ============================================================================

VIBE_INTAKE_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for competitor websites, industry examples, design inspiration, and business information. Use this proactively when the user mentions businesses they like or to research their industry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query. Be specific: 'doula website central NJ' or 'modern salon website design examples'"
                },
                "intent": {
                    "type": "string",
                    "enum": ["competitor_research", "design_inspiration", "industry_info", "local_business"],
                    "description": "Why you're searching - helps contextualize results"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "screenshot_website",
        "description": "Capture a screenshot of a website to show the user. Use this to share design examples, competitor sites, or inspiration. The screenshot URL will be included in your response so the user can see it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL of the website to screenshot (e.g., https://example.com)"
                },
                "description": {
                    "type": "string",
                    "description": "Brief note about why this site is relevant (e.g., 'Clean doula website with good booking flow')"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "memory_search",
        "description": "Search your memory for past projects, lessons learned, and design patterns. Use this to recall what worked well in similar projects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for: 'doula website', 'booking integration', 'color palette for wellness'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "save_inspiration",
        "description": "Save a website or design element as inspiration for this project. These will be referenced during the design phase.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the inspiration source"
                },
                "category": {
                    "type": "string",
                    "enum": ["layout", "colors", "typography", "features", "overall_style"],
                    "description": "What aspect of this site is inspiring"
                },
                "notes": {
                    "type": "string",
                    "description": "What specifically you like about this (e.g., 'Warm color palette with peach accents')"
                }
            },
            "required": ["url", "category", "notes"]
        }
    },
    {
        "name": "deep_research",
        "description": "Conduct deep web research using Google Search. Use this for comprehensive research on topics like industry trends, competitor analysis, design patterns, or technical information. Returns detailed findings with sources and citations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Research query. Be specific: 'doula website design trends 2024' or 'best booking systems for wellness businesses'"
                },
                "research_type": {
                    "type": "string",
                    "enum": ["general", "vibe_inspiration", "competitor", "technical"],
                    "description": "Type of research: general (broad), vibe_inspiration (design focus), competitor (analysis), technical (docs/code)"
                }
            },
            "required": ["query"]
        }
    }
]


ARCHITECTURE_SYSTEM_PROMPT = """You are Nicole, a senior technical architect designing websites for production.

## Your Task
Create a detailed technical specification that the Build phase will use to generate code. Be SPECIFIC - this spec drives everything.

## Output Requirements
Generate a comprehensive JSON specification with these sections:

```json
{
  "project_name": "business-name-website",
  "pages": [
    {
      "path": "/",
      "name": "Homepage",
      "sections": [
        {
          "component": "HeroWithBooking",
          "purpose": "Main headline, value prop, and CTA button",
          "content": {
            "headline": "Actual headline text from brief",
            "subheadline": "Supporting text",
            "cta_text": "Book Now",
            "cta_action": "scroll to contact"
          }
        },
        {
          "component": "ServiceCards",
          "purpose": "Display 3-4 main services",
          "content": {
            "services": ["Service 1 name", "Service 2 name", "Service 3 name"]
          }
        }
      ]
    }
  ],
  "design_system": {
    "colors": {
      "primary": "#hexcode - describe usage (headers, buttons)",
      "secondary": "#hexcode - describe usage (backgrounds, cards)",
      "accent": "#hexcode - describe usage (CTAs, highlights)",
      "text": "#333333",
      "text_light": "#666666"
    },
    "typography": {
      "heading_font": "Playfair Display",
      "body_font": "Source Sans Pro",
      "heading_weight": "700",
      "body_weight": "400"
    },
    "spacing": {
      "section_padding": "py-16 md:py-24",
      "container": "max-w-7xl mx-auto px-4"
    }
  },
  "components": [
    {
      "name": "Header",
      "type": "layout",
      "features": ["logo", "nav links", "mobile menu", "CTA button"]
    },
    {
      "name": "Footer",
      "type": "layout",
      "features": ["logo", "quick links", "contact info", "social links", "copyright"]
    }
  ],
  "content": {
    "business_name": "From the brief",
    "tagline": "From the brief or generate appropriate",
    "phone": "If provided",
    "email": "If provided",
    "address": "If provided",
    "testimonials": [
      {"name": "First Name L.", "location": "City, State", "quote": "Testimonial text", "rating": 5}
    ]
  },
  "seo": {
    "title": "Page title | Business Name",
    "description": "Meta description for SEO",
    "keywords": ["keyword1", "keyword2"]
  }
}
```

## Design Philosophy
- Choose colors that match the business type and tone
- Select fonts that convey the right personality
- Plan sections that tell the business story
- Include social proof (testimonials) and clear CTAs
```

## Guidelines
- Most SMB sites need 4-6 pages maximum
- Prioritize mobile-first responsive design
- Include clear CTAs on every page
- Ensure accessibility compliance (WCAG 2.1 AA)
- Reference the client brief directly - use their brand colors, business type, and goals"""


BUILD_SYSTEM_PROMPT = """You are Nicole, a senior frontend engineer building production websites.

## CRITICAL: Code Quality Standards

You generate code like a senior engineer at a top agency:
- **Complete, production-ready code** - No TODOs, no placeholders, no "..."
- **Consistent design system** - Same spacing, colors, typography throughout
- **Professional content** - Real copy, not "Lorem ipsum" (use business context from brief)
- **Modern patterns** - Clean component structure, proper TypeScript types

## Tech Stack
- Next.js 14 (App Router)
- TypeScript (strict mode)
- Tailwind CSS
- Google Fonts via next/font

## File Generation Order (IMPORTANT)
Generate files in this EXACT order to ensure imports resolve:

### 1. Design Foundation (generate these FIRST)
```filepath:tailwind.config.ts
```
- Define ALL brand colors as theme extensions
- Set font families matching the brief
- Configure spacing scale

```filepath:app/globals.css
```
- @tailwind directives
- CSS custom properties for brand colors
- Base typography styles
- Component utility classes (btn-primary, section-padding, etc.)

### 2. Layout Shell
```filepath:app/layout.tsx
```
- Import fonts with next/font
- Apply font CSS variables
- Include Header and Footer
- Complete metadata

### 3. Shared Components (generate BEFORE pages)
```filepath:components/Header.tsx
```
```filepath:components/Footer.tsx
```
- Export as default
- Use consistent styling from design system

### 4. Page Components
```filepath:components/Hero.tsx
```
(etc. - one component per feature)
- Props with TypeScript interfaces
- Semantic HTML structure
- Responsive design (mobile-first)

### 5. Pages
```filepath:app/page.tsx
```
- Import and compose components
- Server component by default

## Component Pattern Template
Every component should follow this structure:

```typescript
// Good: Clean, typed, complete
interface HeroProps {
  headline: string;
  subheadline: string;
}

export default function Hero({ headline, subheadline }: HeroProps) {
  return (
    <section className="relative bg-gradient-to-b from-sage/10 to-white py-20">
      <div className="container mx-auto px-4 text-center">
        <h1 className="font-heading text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 mb-6">
          {headline}
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          {subheadline}
        </p>
      </div>
    </section>
  );
}
```

## Content Standards
- Use REAL content based on the brief (business name, services, location)
- Write professional copy that matches the business tone
- Include realistic testimonials with names and locations from the area
- Craft CTAs that match the business goals

## File Output Format
Use EXACTLY this pattern:

```filepath:path/to/file.tsx
[complete file contents]
```

NEVER use abbreviated code like "// ... rest of component"
- Glen is counting on you to produce code that works on first run"""


QA_SYSTEM_PROMPT = """You are Nicole, leading the **QA Phase** in the AlphaWave Vibe Dashboard.

## Your Role
You're Glen's AI partner. You've completed Brief, Architecture, and Build. Now you're running quality assurance before final review. Glen sees this as the "Test" step in the dashboard.

## The Vibe Dashboard Workflow
1. ✅ **Brief** - COMPLETE
2. ✅ **Plan** - COMPLETE
3. ✅ **Build** - COMPLETE (code generated)
4. ➡️ **Test** - YOU ARE HERE - QA validation
5. ⏳ **Review** - Next: Final review
6. ⏳ **Ship** - Finally: Deploy

## Your Task
Review the generated code for production readiness. Be thorough but constructive - this is code YOU generated in the Build phase, so catch any issues before Glen's final review.

## QA Checklist

### 1. TypeScript Errors
- Type mismatches
- Missing type annotations
- Incorrect generic usage

### 2. React/Next.js Issues
- Missing 'use client' directives
- Incorrect metadata exports
- Server/client component misuse
- Missing error boundaries

### 3. Import Problems
- Missing imports
- Incorrect import paths
- Circular dependencies

### 4. Accessibility (WCAG 2.1 AA)
- Missing alt text
- Improper heading hierarchy
- Keyboard navigation issues
- Color contrast problems

### 5. SEO Issues
- Missing meta tags
- Improper heading structure
- Missing structured data

### 6. Performance Concerns
- Unnecessary client components
- Missing image optimization
- Bundle size issues

### 7. Brief Alignment
- Does it match the client requirements?
- Are all requested pages present?
- Are brand colors correctly applied?

## Output Format
```json
{
  "passed": true|false,
  "score": 1-100,
  "issues": [
    {"severity": "critical|high|medium|low", "file": "path", "line": null, "message": "description"}
  ],
  "suggestions": ["improvement suggestion"],
  "summary": "Overall assessment for Glen"
}
```

Be honest about issues - better to catch them now than after deployment!"""


REVIEW_SYSTEM_PROMPT = """You are Nicole, leading the **Review Phase** in the AlphaWave Vibe Dashboard.

## Your Role
You're Glen's AI partner. This is the final checkpoint before deployment. You've led this project through Brief, Plan, Build, and QA - now make the final call on whether it's ready for the client.

## The Vibe Dashboard Workflow
1. ✅ **Brief** - COMPLETE
2. ✅ **Plan** - COMPLETE  
3. ✅ **Build** - COMPLETE
4. ✅ **Test** - COMPLETE (QA passed)
5. ➡️ **Review** - YOU ARE HERE - Final decision
6. ⏳ **Ship** - Next: Deploy to production

## Your Task
Conduct a comprehensive final review. This is the last stop before Glen approves and deploys to the client. Be thorough but remember - you built this, you tested it, now confirm it's ready.

## Review Criteria

### 1. Brief Alignment
Does the implementation match ALL client requirements?
- Business name, colors, content
- All requested pages and features
- Contact information accurate
- Goal alignment (bookings, leads, etc.)

### 2. Architecture Compliance
Is the technical spec properly implemented?
- All planned pages exist
- Components match specification
- Integrations working

### 3. Code Quality
Is the code production-ready and maintainable?
- TypeScript strict mode passing
- No console errors
- Proper error handling
- Clean, readable code

### 4. User Experience
Is the site professional and user-friendly?
- Mobile responsive
- Fast loading
- Intuitive navigation
- Accessible

### 5. Business Value
Would this site help the client achieve their goals?
- Clear CTAs
- Professional appearance
- Trust-building elements
- Easy to contact/book

## Output Format
```json
{
  "approved": true|false,
  "score": 1-10,
  "brief_alignment": {"score": 1-10, "notes": "..."},
  "code_quality": {"score": 1-10, "notes": "..."},
  "ux_quality": {"score": 1-10, "notes": "..."},
  "strengths": ["strength1", "strength2"],
  "concerns": ["concern1", "concern2"],
  "required_changes": ["change1"] | null,
  "recommendation": "approve|revise|reject",
  "client_ready": true|false,
  "message_to_glen": "Your summary for Glen about this project"
}
```

## Remember
- Be honest with Glen - if something needs fixing, say so
- If it's good, approve it confidently
- This is YOUR work - you led every phase. Own the result."""


# ============================================================================
# EXCEPTIONS
# ============================================================================

class VibeServiceError(Exception):
    """Base exception for Vibe service errors."""
    pass


class ProjectNotFoundError(VibeServiceError):
    """Project does not exist or user doesn't have access."""
    pass


class InvalidStatusTransitionError(VibeServiceError):
    """Invalid status transition attempted."""
    pass


class MissingPrerequisiteError(VibeServiceError):
    """Required data missing for operation."""
    pass


class ConcurrencyError(VibeServiceError):
    """Concurrent modification detected."""
    pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def estimate_api_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Estimate API cost for a Claude call."""
    costs = MODEL_COSTS.get(model, MODEL_COSTS["claude-sonnet-4-5-20250929"])
    # Use Decimal throughout to avoid Decimal * float error
    input_cost = Decimal(str(costs["input"])) * Decimal(str(input_tokens)) / Decimal("1000")
    output_cost = Decimal(str(costs["output"])) * Decimal(str(output_tokens)) / Decimal("1000")
    return input_cost + output_cost


def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from Claude's response, handling various formats."""
    # Try ```json blocks first
    json_pattern = r'```json\s*(.*?)\s*```'
    matches = re.findall(json_pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    # Try generic ``` blocks
    generic_pattern = r'```\s*(.*?)\s*```'
    matches = re.findall(generic_pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    # Try parsing the entire response as JSON
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass
    
    return None


def parse_files_from_response(response: str) -> List[ParsedFile]:
    """
    Parse file contents from Claude's response.
    
    Supports multiple formats (in order of specificity):
    1. ```filepath:/path/to/file.tsx - explicit filepath
    2. **path/to/file.tsx** header followed by code block
    3. `path/to/file.tsx` header followed by code block  
    4. ### path/to/file.tsx header followed by code block
    5. ```lang with // filepath or /* filepath */ comment
    6. === filename.tsx === headers
    7. File: path/to/file.tsx followed by code block
    """
    files: List[ParsedFile] = []
    seen_paths: set = set()
    
    def add_file(path: str, content: str) -> bool:
        """Helper to add a file if valid and not seen."""
        path = path.strip().lstrip('/')
        content = content.strip()
        if path and content and path not in seen_paths and len(content) > 10:
            files.append(ParsedFile(
                path=path,
                content=content,
                language=ParsedFile.detect_language(path)
            ))
            seen_paths.add(path)
            return True
        return False
    
    # Use pre-compiled regex patterns for performance
    
    # Pattern 1: ```filepath:/path/to/file (most explicit)
    for match in RE_FILEPATH_BLOCK.finditer(response):
        add_file(match.group(1), match.group(2))
    
    # Pattern 2: **path/to/file.tsx** followed by code block
    for match in RE_BOLD_HEADER.finditer(response):
        add_file(match.group(1), match.group(2))
    
    # Pattern 3: `path/to/file.tsx` followed by code block
    for match in RE_BACKTICK_HEADER.finditer(response):
        add_file(match.group(1), match.group(2))
    
    # Pattern 4: ### path/to/file.tsx header
    for match in RE_MARKDOWN_HEADER.finditer(response):
        add_file(match.group(1), match.group(2))
    
    # Pattern 5a: ```lang with // filepath comment on first line
    for match in RE_COMMENT_FILEPATH.finditer(response):
        add_file(match.group(1), match.group(2))
    
    # Pattern 5b: ```lang with /* filepath */ comment on first line
    for match in RE_BLOCK_COMMENT_FILEPATH.finditer(response):
        add_file(match.group(1), match.group(2))
    
    # Pattern 6: === filename.ext === headers
    for match in RE_SEPARATOR_HEADER.finditer(response):
        path = match.group(1).strip()
        content = match.group(2).strip()
        # Clean content: remove leading/trailing code blocks
        if '```' in content:
            code_match = RE_CODE_BLOCK.search(content)
            if code_match:
                content = code_match.group(1).strip()
        add_file(path, content)
    
    # Pattern 7: File: path/to/file.tsx followed by code block
    for match in RE_FILE_LABEL.finditer(response):
        add_file(match.group(1), match.group(2))
    
    if not files:
        logger.warning("[VIBE] No files parsed from build response. Response preview: %s...", 
                      response[:500] if response else "empty")
    else:
        logger.info("[VIBE] Parsed %d files from response", len(files))
    
    return files


# ============================================================================
# SERVICE CLASS
# ============================================================================

class VibeService:
    """
    Production-grade service for AlphaWave Vibe project management.
    
    Features:
    - Type-safe status transitions
    - Transaction support for multi-step operations
    - API cost tracking
    - Comprehensive error handling
    - Lessons learning system
    """
    
    # Model configuration - Latest Claude versions
    SONNET_MODEL = "claude-sonnet-4-5-20250929"
    OPUS_MODEL = "claude-opus-4-5-20251101"
    
    def __init__(self):
        """Initialize the Vibe service."""
        self._inspiration_cache: Dict[int, List[Dict[str, Any]]] = {}  # project_id -> inspirations
        logger.info("[VIBE] Service initialized (v2.0 with tools)")
    
    # ========================================================================
    # VIBE TOOL EXECUTOR
    # ========================================================================
    
    async def _execute_vibe_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        project_id: int
    ) -> Dict[str, Any]:
        """
        Execute a Vibe intake tool and return the result.
        
        Tools available:
        - web_search: Search the web for competitors/inspiration
        - screenshot_website: Capture a website screenshot
        - memory_search: Search past project lessons
        - save_inspiration: Save a site for later reference
        
        Returns:
            Dict with 'success', 'result', and optionally 'image_url'
        """
        try:
            if tool_name == "web_search":
                return await self._tool_web_search(
                    query=tool_input.get("query", ""),
                    intent=tool_input.get("intent", "general")
                )
            
            elif tool_name == "screenshot_website":
                return await self._tool_screenshot(
                    url=tool_input.get("url", ""),
                    description=tool_input.get("description", ""),
                    project_id=project_id
                )
            
            elif tool_name == "memory_search":
                return await self._tool_memory_search(
                    query=tool_input.get("query", ""),
                    project_id=project_id
                )
            
            elif tool_name == "save_inspiration":
                return await self._tool_save_inspiration(
                    url=tool_input.get("url", ""),
                    category=tool_input.get("category", "overall_style"),
                    notes=tool_input.get("notes", ""),
                    project_id=project_id
                )
            
            elif tool_name == "deep_research":
                return await self._tool_deep_research(
                    query=tool_input.get("query", ""),
                    research_type=tool_input.get("research_type", "general"),
                    project_id=project_id
                )
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
                
        except Exception as e:
            logger.error(f"[VIBE] Tool {tool_name} failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _tool_web_search(self, query: str, intent: str) -> Dict[str, Any]:
        """Execute web search using Docker MCP Gateway (Brave Search) or Gemini fallback."""
        
        try:
            # Try Docker MCP Gateway first (this is the PRIMARY MCP system)
            from app.mcp.docker_mcp_client import get_mcp_client
            
            try:
                mcp = await get_mcp_client()
                if mcp.is_connected:
                    # Call Brave Search via Docker MCP Gateway
                    result = await mcp.call_tool("brave_web_search", {"query": query, "count": 5})
                    
                    if not result.is_error and result.content:
                        # Parse the response
                        import json as json_module
                        try:
                            if isinstance(result.content, str):
                                data = json_module.loads(result.content)
                            else:
                                data = result.content
                            
                            formatted = []
                            web_results = data.get("web", {}).get("results", []) if isinstance(data, dict) else []
                            for r in web_results[:5]:
                                formatted.append({
                                    "title": r.get("title", ""),
                                    "url": r.get("url", ""),
                                    "description": r.get("description", "")[:200]
                                })
                            
                            if formatted:
                                logger.info(f"[VIBE] Brave Search via Docker MCP returned {len(formatted)} results")
                                return {
                                    "success": True,
                                    "result": {
                                        "query": query,
                                        "intent": intent,
                                        "results": formatted,
                                        "result_count": len(formatted),
                                        "source": "brave_search_docker"
                                    }
                                }
                        except json_module.JSONDecodeError:
                            logger.warning(f"[VIBE] Failed to parse Brave Search response")
            except Exception as e:
                logger.warning(f"[VIBE] Docker MCP Gateway not available: {e}")
            
            # Fallback: Try legacy MCP manager
            from app.mcp import call_mcp_tool, mcp_manager, AlphawaveMCPManager
            
            if isinstance(mcp_manager, AlphawaveMCPManager):
                server_status = mcp_manager.get_server_status("brave-search")
                from app.mcp.alphawave_mcp_manager import MCPServerStatus
                if server_status == MCPServerStatus.CONNECTED:
                    result = await call_mcp_tool(
                        "brave-search",
                        "brave_web_search",
                        {"query": query, "count": 5}
                    )
                    
                    if result and not result.get("error"):
                        formatted = []
                        web_results = result.get("web", {}).get("results", [])
                        for r in web_results[:5]:
                            formatted.append({
                                "title": r.get("title", ""),
                                "url": r.get("url", ""),
                                "description": r.get("description", "")[:200]
                            })
                        
                        return {
                            "success": True,
                            "result": {
                                "query": query,
                                "intent": intent,
                                "results": formatted,
                                "result_count": len(formatted),
                                "source": "brave_search_legacy"
                            }
                        }
            
            # Fallback: Use Gemini deep_research for web search
            logger.info(f"[VIBE] Using Gemini fallback for web search: {query}")
            from app.integrations.alphawave_gemini import gemini_client, ResearchType
            
            # Map intent to research type
            rt_map = {
                "competitor_research": ResearchType.COMPETITOR,
                "design_inspiration": ResearchType.VIBE_INSPIRATION,
                "industry_info": ResearchType.GENERAL,
                "local_business": ResearchType.GENERAL
            }
            rt = rt_map.get(intent, ResearchType.GENERAL)
            
            result = await gemini_client.deep_research(
                query=query,
                research_type=rt,
                max_sources=5,
                enable_thinking=False  # Faster for simple searches
            )
            
            if result.get("success"):
                sources = result.get("sources", [])
                parsed = result.get("results", {})
                
                return {
                    "success": True,
                    "result": {
                        "query": query,
                        "intent": intent,
                        "results": [
                            {"title": s.get("title", ""), "url": s.get("url", ""), "description": s.get("snippet", "")[:200]}
                            for s in sources[:5]
                        ],
                        "summary": parsed.get("executive_summary", ""),
                        "result_count": len(sources),
                        "source": "gemini_research"
                    }
                }
            
            # If Gemini also fails, return helpful message
            return {
                "success": True,
                "result": {
                    "query": query,
                    "intent": intent,
                    "results": [],
                    "message": f"Research for '{query}' is processing. I'll proceed with available information and you can share specific URLs you like."
                }
            }
            
        except Exception as e:
            logger.warning(f"[VIBE] Web search failed: {e}")
            return {
                "success": True,  # Return success with empty results rather than failing
                "result": {
                    "query": query,
                    "intent": intent,
                    "results": [],
                    "message": f"Search temporarily unavailable. Please share any specific websites you'd like me to reference."
                }
            }
    
    async def _tool_screenshot(
        self, 
        url: str, 
        description: str,
        project_id: int
    ) -> Dict[str, Any]:
        """
        Capture a website screenshot using Docker MCP Gateway (Puppeteer) and store in Cloudinary.
        
        Flow:
        1. Try Docker MCP Gateway for Puppeteer screenshot
        2. Fall back to legacy Playwright MCP
        3. Upload base64 image to Cloudinary
        4. Store reference in inspiration cache
        5. Return permanent URL
        """
        from app.services.alphawave_cloudinary_service import cloudinary_service
        
        # Get project name for folder organization
        project = await self.get_project(user_id=0, project_id=project_id)
        project_name = project.data.get("name", f"project_{project_id}") if project.success else f"project_{project_id}"
        project_slug = project_name.lower().replace(" ", "-")[:30]
        
        screenshot_url = None
        base64_data = None
        
        # Try Docker MCP Gateway first (Puppeteer)
        try:
            from app.mcp.docker_mcp_client import get_mcp_client
            mcp = await get_mcp_client()
            
            if mcp.is_connected:
                # Check if puppeteer tools are available
                tools = await mcp.list_tools()
                puppeteer_tools = [t for t in tools if "puppeteer" in t.name.lower()]
                
                if puppeteer_tools:
                    # Navigate to URL
                    nav_result = await mcp.call_tool("puppeteer_navigate", {"url": url})
                    if not nav_result.is_error:
                        # Take screenshot
                        screenshot_result = await mcp.call_tool("puppeteer_screenshot", {})
                        
                        if not screenshot_result.is_error and screenshot_result.content:
                            # Parse base64 from result
                            content = screenshot_result.content
                            if isinstance(content, str):
                                # Look for base64 data
                                import json as json_module
                                try:
                                    data = json_module.loads(content)
                                    base64_data = data.get("data") or data.get("screenshot")
                                except:
                                    # Content might be the base64 directly
                                    if len(content) > 100 and "," not in content[:50]:
                                        base64_data = content
                            logger.info(f"[VIBE] Screenshot captured via Docker MCP Gateway")
        except Exception as e:
            logger.warning(f"[VIBE] Docker MCP screenshot failed: {e}")
        
        # Fall back to legacy Playwright MCP
        if not base64_data:
            try:
                from app.mcp.alphawave_playwright_mcp import playwright_mcp
                
                if playwright_mcp.is_connected or await playwright_mcp.connect():
                    # Navigate to URL
                    await playwright_mcp.navigate(url, wait_until="networkidle")
                    
                    # Take screenshot
                    result = await playwright_mcp.screenshot(full_page=False, format="png")
                    
                    if result and not result.get("error"):
                        base64_data = result.get("data") or result.get("screenshot")
                        logger.info(f"[VIBE] Screenshot captured via legacy Playwright MCP")
            except Exception as e:
                logger.warning(f"[VIBE] Legacy Playwright MCP screenshot failed: {e}")
        
        # Upload to Cloudinary if we have screenshot data
        if base64_data and cloudinary_service.is_configured:
            try:
                upload_result = await cloudinary_service.upload_screenshot(
                    base64_data=base64_data,
                    project_name=project_slug,
                    description=description,
                    url_source=url
                )
                
                if upload_result.get("success"):
                    screenshot_url = upload_result.get("url")
                    logger.info(f"[VIBE] Screenshot uploaded to Cloudinary: {screenshot_url}")
            except Exception as e:
                logger.warning(f"[VIBE] Cloudinary upload failed: {e}")
        
        # Store in inspiration cache AND database for persistence
        inspiration_data = {
            "url": url,
            "description": description,
            "type": "screenshot" if screenshot_url else "screenshot_reference",
            "image_url": screenshot_url,
            "captured_at": datetime.now().isoformat()
        }
        
        if project_id not in self._inspiration_cache:
            self._inspiration_cache[project_id] = []
        self._inspiration_cache[project_id].append(inspiration_data)
        
        # Persist to database
        try:
            await db.execute(
                """
                INSERT INTO vibe_inspirations 
                (project_id, image_url, screenshot_url, source_site, relevance_notes, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                """,
                project_id, url, screenshot_url, url, description
            )
            logger.info(f"[VIBE] Inspiration saved to database for project {project_id}")
        except Exception as e:
            logger.warning(f"[VIBE] Failed to persist inspiration to DB: {e}")
        
        if screenshot_url:
            return {
                "success": True,
                "result": {
                    "url": url,
                    "description": description,
                    "image_url": screenshot_url,
                    "message": f"Screenshot captured and saved: {description}"
                }
            }
        else:
            # Fallback to reference
            return {
                "success": True,
                "result": {
                    "url": url,
                    "description": description,
                    "message": f"Referenced {url} for inspiration (screenshot service unavailable)"
                }
            }
    
    async def _tool_memory_search(
        self, 
        query: str,
        project_id: int
    ) -> Dict[str, Any]:
        """Search past lessons and project patterns."""
        try:
            # Search lessons
            lessons, _ = await self.get_relevant_lessons(
                project_type="website",
                category=None,
                query=query,
                limit=3
            )
            
            if lessons:
                return {
                    "success": True,
                    "result": {
                        "query": query,
                        "lessons": [
                            {
                                "issue": l.get("issue", ""),
                                "solution": l.get("solution", ""),
                                "impact": l.get("impact", ""),
                                "category": l.get("lesson_category", "")
                            }
                            for l in lessons
                        ],
                        "message": f"Found {len(lessons)} relevant lessons from past projects"
                    }
                }
            
            return {
                "success": True,
                "result": {
                    "query": query,
                    "lessons": [],
                    "message": "No previous lessons found for this query"
                }
            }
            
        except Exception as e:
            logger.warning(f"[VIBE] Memory search failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _tool_save_inspiration(
        self,
        url: str,
        category: str,
        notes: str,
        project_id: int
    ) -> Dict[str, Any]:
        """Save a URL as inspiration for the project."""
        if project_id not in self._inspiration_cache:
            self._inspiration_cache[project_id] = []
        
        inspiration = {
            "url": url,
            "category": category,
            "notes": notes,
            "saved_at": datetime.now().isoformat()
        }
        
        self._inspiration_cache[project_id].append(inspiration)
        
        # Also save to database if we want persistence
        try:
            await self._log_activity(
                project_id=project_id,
                activity_type=ActivityType.INTAKE_MESSAGE,
                description=f"Saved inspiration: {url}",
                agent_name="Nicole",
                metadata=inspiration
            )
        except Exception as e:
            logger.warning(f"[VIBE] Failed to log inspiration: {e}")
        
        return {
            "success": True,
            "result": {
                "url": url,
                "category": category,
                "notes": notes,
                "message": f"Saved {url} as {category} inspiration"
            }
        }
    
    async def _tool_deep_research(
        self,
        query: str,
        research_type: str,
        project_id: int
    ) -> Dict[str, Any]:
        """
        Execute deep research using Gemini 3 Pro with Google Search grounding.
        
        This provides comprehensive research with citations and sources.
        """
        from app.integrations.alphawave_gemini import gemini_client, ResearchType
        
        # Map string to enum
        try:
            rt = ResearchType(research_type)
        except ValueError:
            rt = ResearchType.GENERAL
        
        # Get project context using internal method (no user validation needed for tools)
        context = None
        if project_id:
            project = await self._get_project_internal(project_id)
            if project:
                context = {
                    "project_brief": project.get("brief"),
                    "project_name": project.get("name"),
                    "project_type": project.get("project_type"),
                    "status": project.get("status"),
                    "intake_summary": project.get("intake_summary")
                }
        
        # Execute research
        result = await gemini_client.deep_research(
            query=query,
            research_type=rt,
            context=context,
            enable_thinking=True
        )
        
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Research failed")
            }
        
        # Format results for Nicole to present
        parsed = result.get("results", {})
        sources = result.get("sources", [])
        
        # Log research activity
        try:
            await self._log_activity(
                project_id=project_id,
                activity_type=ActivityType.INTAKE_MESSAGE,
                description=f"Deep research: {query[:50]}...",
                agent_name="Nicole",
                metadata={
                    "query": query,
                    "research_type": research_type,
                    "source_count": len(sources),
                    "cost_usd": result.get("metadata", {}).get("cost_usd", 0)
                }
            )
        except Exception as e:
            logger.warning(f"[VIBE] Failed to log research: {e}")
        
        return {
            "success": True,
            "result": {
                "query": query,
                "research_type": research_type,
                "executive_summary": parsed.get("executive_summary", ""),
                "key_findings": parsed.get("key_findings", [])[:5],  # Top 5 findings
                "recommendations": parsed.get("recommendations", [])[:3],
                "sources": [
                    {"url": s.get("url", ""), "title": s.get("title", "")}
                    for s in sources[:5]
                ],
                "message": f"Research complete. Found {len(sources)} relevant sources."
            }
        }
    
    async def get_project_inspirations(self, project_id: int) -> List[Dict[str, Any]]:
        """Get saved inspirations for a project from database and cache."""
        # First check cache for any recent (non-persisted) inspirations
        cached = self._inspiration_cache.get(project_id, [])
        
        # Load from database
        try:
            rows = await db.fetch(
                """
                SELECT id, image_url, screenshot_url, source_site, relevance_notes, created_at
                FROM vibe_inspirations
                WHERE project_id = $1
                ORDER BY created_at DESC
                LIMIT 50
                """,
                project_id
            )
            
            db_inspirations = [
                {
                    "id": row["id"],
                    "url": row["image_url"] or row["source_site"],
                    "image_url": row["screenshot_url"],
                    "description": row["relevance_notes"],
                    "type": "screenshot" if row["screenshot_url"] else "reference",
                    "captured_at": row["created_at"].isoformat() if row["created_at"] else None
                }
                for row in (rows or [])
            ]
            
            # Merge with cache (cache may have items not yet in DB)
            # Use URL as dedup key
            seen_urls = {i.get("url") for i in db_inspirations}
            for cached_item in cached:
                if cached_item.get("url") not in seen_urls:
                    db_inspirations.append(cached_item)
            
            return db_inspirations
            
        except Exception as e:
            logger.warning(f"[VIBE] Failed to load inspirations from DB: {e}")
            return cached
    
    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================
    
    async def _get_project_or_raise(
        self, 
        project_id: int, 
        user_id: int
    ) -> Dict[str, Any]:
        """Get project or raise ProjectNotFoundError."""
        result = await db.fetchrow(
            """
            SELECT * FROM vibe_projects 
            WHERE project_id = $1 AND user_id = $2
            """,
            project_id, user_id
        )
        
        if not result:
            raise ProjectNotFoundError(f"Project {project_id} not found or access denied")
        
        return dict(result)
    
    def _validate_status_for_operation(
        self,
        project: Dict[str, Any],
        allowed_statuses: List[ProjectStatus],
        operation_name: str
    ) -> None:
        """Validate project status for an operation."""
        current_status = project.get("status", "")
        
        try:
            status_enum = ProjectStatus(current_status)
        except ValueError:
            raise InvalidStatusTransitionError(
                f"Invalid project status: {current_status}"
            )
        
        if status_enum not in allowed_statuses:
            allowed_names = ", ".join(s.value for s in allowed_statuses)
            raise InvalidStatusTransitionError(
                f"{operation_name} requires status to be one of: {allowed_names}. "
                f"Current status: {current_status}"
            )
    
    async def _generate_embedding_safe(self, text: str) -> Optional[List[float]]:
        """Generate embedding with retry and graceful fallback."""
        attempts = 2
        for attempt in range(attempts):
            try:
                return await openai_client.generate_embedding(text)
            except Exception as e:
                logger.warning("[VIBE] Embedding attempt %d failed: %s", attempt + 1, e, exc_info=True)
        return None
    
    async def _call_claude_with_retry(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        model: str,
        max_tokens: int = 4000,
        temperature: float = 0.5,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> str:
        """
        Call Claude API with exponential backoff retry.
        
        Args:
            messages: Chat messages
            system_prompt: System prompt
            model: Model name
            max_tokens: Max response tokens
            temperature: Generation temperature
            max_retries: Maximum retry attempts
            base_delay: Initial delay in seconds (doubles each retry)
            
        Returns:
            Generated response text
            
        Raises:
            Exception: If all retries fail
        """
        import asyncio
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await claude_client.generate_response(
                    messages=messages,
                    system_prompt=system_prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check for overload/rate limit errors - use longer delays
                is_overload = "529" in error_str or "overload" in error_str or "rate" in error_str
                
                if attempt < max_retries - 1:
                    # Longer delay for overload errors
                    delay = base_delay * (2 ** attempt) * (3 if is_overload else 1)
                    logger.warning(
                        "[VIBE] Claude call attempt %d/%d failed: %s. Retrying in %.1fs...",
                        attempt + 1, max_retries, e, delay
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "[VIBE] Claude call failed after %d attempts: %s",
                        max_retries, e, exc_info=True
                    )
        
        # Create user-friendly error message
        error_str = str(last_error).lower() if last_error else ""
        if "529" in error_str or "overload" in error_str:
            raise Exception("Claude AI is temporarily overloaded. Please wait a moment and try again.")
        elif "rate" in error_str:
            raise Exception("Rate limit reached. Please wait a moment before retrying.")
        elif "timeout" in error_str:
            raise Exception("Request timed out. Please try again.")
        else:
            raise last_error or Exception("AI service temporarily unavailable. Please retry.")
    
    async def _update_api_cost(
        self,
        project_id: int,
        user_id: int,
        cost: Decimal
    ) -> None:
        """Add to project's cumulative API cost.
        
        Uses string representation to preserve Decimal precision
        when passing to PostgreSQL DECIMAL column.
        """
        await db.execute(
            """
            UPDATE vibe_projects
            SET api_cost = COALESCE(api_cost, 0) + $1::DECIMAL, updated_at = NOW()
            WHERE project_id = $2 AND user_id = $3
            """,
            str(cost), project_id, user_id
        )
    
    async def _save_files_batch(
        self,
        project_id: int,
        files: List[ParsedFile],
        user_id: Optional[int] = None,
        agent_name: Optional[str] = None,
        conn=None
    ) -> int:
        """
        Save multiple files with non-destructive upsert and change logging.
        
        Args:
            project_id: Project to save files for
            files: List of ParsedFile objects
            user_id: User performing the operation
            agent_name: AI agent name if applicable
            conn: Optional database connection for transaction support
        """
        if not files:
            return 0
        
        # Use provided connection or acquire new one
        if conn:
            existing_rows = await conn.fetch(
                "SELECT file_path, content FROM vibe_files WHERE project_id = $1",
                project_id
            )
        else:
            existing_rows = await db.fetch(
                "SELECT file_path, content FROM vibe_files WHERE project_id = $1",
                project_id
            )
        existing_map = {r["file_path"]: r["content"] for r in existing_rows} if existing_rows else {}
        
        count = 0
        changes_to_log = []  # Collect changes to log after all files saved
        
        for f in files:
            previous_content = existing_map.get(f.path)
            
            if conn:
                await conn.execute(
                    """
                    INSERT INTO vibe_files (project_id, file_path, content, created_at, updated_at)
                    VALUES ($1, $2, $3, NOW(), NOW())
                    ON CONFLICT (project_id, file_path)
                    DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
                    """,
                    project_id, f.path, f.content
                )
            else:
                await db.execute(
                    """
                    INSERT INTO vibe_files (project_id, file_path, content, created_at, updated_at)
                    VALUES ($1, $2, $3, NOW(), NOW())
                    ON CONFLICT (project_id, file_path)
                    DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
                    """,
                    project_id, f.path, f.content
                )
            count += 1
            
            # Track file changes for logging
            if previous_content is None:
                changes_to_log.append({
                    "type": "added",
                    "path": f.path,
                    "metadata": {"path": f.path, "change": "added"}
                })
            elif previous_content != f.content:
                changes_to_log.append({
                    "type": "modified",
                    "path": f.path,
                    "metadata": {
                        "path": f.path,
                        "change": "modified",
                        "previous_preview": previous_content[:200]
                    }
                })
        
        # Log all file changes (can be outside transaction, logging is non-critical)
        for change in changes_to_log:
            await self._log_activity(
                project_id,
                ActivityType.FILE_UPDATED,
                description=f"File {change['type']}: {change['path']}",
                user_id=user_id,
                agent_name=agent_name,
                metadata=change["metadata"]
            )
        
        logger.info("[VIBE] Saved %d files for project %d", count, project_id)
        return count
    
    async def _log_activity(
        self,
        project_id: int,
        activity_type: ActivityType,
        description: str,
        user_id: Optional[int] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an activity to the audit trail.
        
        Args:
            project_id: Project this activity belongs to
            activity_type: Type of activity from ActivityType enum
            description: Human-readable description
            user_id: User who performed the action (None for system)
            agent_name: AI agent name if applicable
            metadata: Additional structured data
        """
        try:
            await db.execute(
                """
                INSERT INTO vibe_activities (
                    project_id, activity_type, description, 
                    user_id, agent_name, metadata, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                """,
                project_id,
                activity_type.value,
                description,
                user_id,
                agent_name,
                json.dumps(metadata) if metadata else '{}',
            )
        except Exception as e:
            # Don't fail operations due to activity logging errors
            logger.warning("[VIBE] Failed to log activity: %s", e, exc_info=True)
    
    async def _log_agent_message(
        self,
        project_id: int,
        agent_name: str,
        message_type: str,  # "prompt", "response", "thinking", "tool_call", "tool_result"
        content: str,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a detailed agent message for the console view.
        
        This provides visibility into what agents are actually doing,
        similar to how Cursor shows Claude's thinking process.
        """
        try:
            # Determine icon based on message type
            icons = {
                "prompt": "📤",
                "response": "📥", 
                "thinking": "💭",
                "tool_call": "🔧",
                "tool_result": "✅",
                "error": "❌",
            }
            icon = icons.get(message_type, "💬")
            
            # Create a detailed description for the activity log
            description = f"{icon} [{message_type.upper()}] {content}"
            
            await db.execute(
                """
                INSERT INTO vibe_activities (
                    project_id, activity_type, description, 
                    user_id, agent_name, metadata, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                """,
                project_id,
                "agent_message",  # Special type for console messages
                description[:500],  # Truncate for DB but keep most content
                user_id,
                agent_name,
                json.dumps({
                    "message_type": message_type,
                    "full_content": content[:2000],  # Store more in metadata
                    **(metadata or {})
                }),
            )
        except Exception as e:
            logger.warning("[VIBE] Failed to log agent message: %s", e, exc_info=True)
    
    async def get_project_activities(
        self,
        project_id: int,
        user_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get activity timeline for a project with user access validation.
        
        Args:
            project_id: Project ID
            user_id: User ID for access validation
            limit: Maximum activities to return
            
        Returns:
            List of activities, newest first
            
        Raises:
            ProjectNotFoundError: If project doesn't exist or user lacks access
        """
        # Validate user has access to project
        await self._get_project_or_raise(project_id, user_id)
        
        results = await db.fetch(
            """
            SELECT 
                activity_id, project_id, activity_type, description,
                user_id, agent_name, metadata, created_at
            FROM vibe_activities
            WHERE project_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            project_id, limit
        )
        return [dict(r) for r in results] if results else []
    
    # ========================================================================
    # PROJECT CRUD
    # ========================================================================
    
    async def create_project(
        self,
        user_id: int,
        name: str,
        project_type: str,
        client_name: Optional[str] = None,
        client_email: Optional[str] = None
    ) -> OperationResult:
        """
        Create a new Vibe project.
        
        Args:
            user_id: Owner's user ID
            name: Project name
            project_type: One of website, chatbot, assistant, integration
            client_name: Optional client business name
            client_email: Optional client email
            
        Returns:
            OperationResult with created project data
        """
        # Validate project type
        try:
            ProjectType(project_type)
        except ValueError:
            return OperationResult(
                success=False,
                error=f"Invalid project type: {project_type}. Must be one of: {', '.join(t.value for t in ProjectType)}"
            )
        
        try:
            result = await db.fetchrow(
                """
                INSERT INTO vibe_projects (
                    user_id, name, project_type, client_name, client_email,
                    status, brief, architecture, config, 
                    api_cost, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, '{}', '{}', '{}', 0, NOW(), NOW())
                RETURNING *
                """,
                user_id, name, project_type, client_name, client_email,
                ProjectStatus.INTAKE.value
            )
            
            if not result:
                return OperationResult(success=False, error="Failed to create project")
            
            project = dict(result)
            logger.info("[VIBE] Created project %d: %s", project['project_id'], name)
            
            # Log activity
            await self._log_activity(
                project_id=project['project_id'],
                activity_type=ActivityType.PROJECT_CREATED,
                description=f"Project '{name}' created",
                user_id=user_id,
                metadata={"project_type": project_type, "client_name": client_name}
            )
            
            return OperationResult(
                success=True,
                data={"project": project, "status": ProjectStatus.INTAKE.value}
            )
            
        except Exception as e:
            logger.error("[VIBE] Failed to create project: %s", e, exc_info=True)
            return OperationResult(success=False, error=str(e))
    
    async def get_project(
        self, 
        project_id: int, 
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a project by ID with user access check. Returns None if not found."""
        result = await db.fetchrow(
            """
            SELECT * FROM vibe_projects 
            WHERE project_id = $1 AND user_id = $2
            """,
            project_id, user_id
        )
        return dict(result) if result else None
    
    async def _get_project_internal(
        self, 
        project_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a project by ID without user access check.
        
        INTERNAL USE ONLY - for system operations like lesson capture
        where user context is not available or relevant.
        """
        result = await db.fetchrow(
            """
            SELECT * FROM vibe_projects 
            WHERE project_id = $1
            """,
            project_id
        )
        return dict(result) if result else None
    
    async def list_projects(
        self, 
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List user's projects with pagination.
        
        Returns:
            Tuple of (projects list, total count)
        """
        # Get total count
        if status:
            count_result = await db.fetchrow(
                "SELECT COUNT(*) as total FROM vibe_projects WHERE user_id = $1 AND status = $2",
                user_id, status
            )
        else:
            count_result = await db.fetchrow(
                "SELECT COUNT(*) as total FROM vibe_projects WHERE user_id = $1 AND status != 'archived'",
                user_id
            )
        
        total = count_result['total'] if count_result else 0
        
        # Get projects
        if status:
            results = await db.fetch(
                """
                SELECT project_id, name, project_type, client_name, client_email,
                       status, preview_url, production_url, api_cost,
                       created_at, updated_at
                FROM vibe_projects
                WHERE user_id = $1 AND status = $2
                ORDER BY updated_at DESC
                LIMIT $3 OFFSET $4
                """,
                user_id, status, limit, offset
            )
        else:
            results = await db.fetch(
                """
                SELECT project_id, name, project_type, client_name, client_email,
                       status, preview_url, production_url, api_cost,
                       created_at, updated_at
                FROM vibe_projects
                WHERE user_id = $1 AND status != 'archived'
                ORDER BY updated_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id, limit, offset
            )
        
        projects = [dict(r) for r in results] if results else []
        return projects, total
    
    async def update_project(
        self,
        project_id: int,
        user_id: int,
        updates: Dict[str, Any]
    ) -> OperationResult:
        """
        Update project fields.
        
        Args:
            project_id: Project to update
            user_id: User making the update
            updates: Dict of field names to new values
            
        Returns:
            OperationResult with updated project
        """
        # Validate project exists
        try:
            await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Whitelist allowed fields
        allowed_fields = {
            'name', 'client_name', 'client_email', 'status',
            'brief', 'architecture', 'config',
            'preview_url', 'production_url', 'github_repo',
            'estimated_price', 'api_cost'
        }
        
        # JSONB fields need special handling
        jsonb_fields = {'brief', 'architecture', 'config'}
        
        set_clauses = []
        values = []
        param_idx = 1
        
        for field, value in updates.items():
            if field not in allowed_fields:
                continue
            
            if field in jsonb_fields:
                # Cast to JSONB explicitly
                set_clauses.append(f"{field} = ${param_idx}::jsonb")
                values.append(json.dumps(value) if isinstance(value, dict) else value)
            else:
                set_clauses.append(f"{field} = ${param_idx}")
                values.append(value)
            param_idx += 1
        
        if not set_clauses:
            project = await self.get_project(project_id, user_id)
            return OperationResult(success=True, data={"project": project})
        
        set_clauses.append("updated_at = NOW()")
        
        query = f"""
            UPDATE vibe_projects
            SET {', '.join(set_clauses)}
            WHERE project_id = ${param_idx} AND user_id = ${param_idx + 1}
            RETURNING *
        """
        
        values.extend([project_id, user_id])
        
        try:
            result = await db.fetchrow(query, *values)
            
            if not result:
                return OperationResult(success=False, error="Update failed")
            
            return OperationResult(
                success=True,
                data={"project": dict(result)}
            )
            
        except Exception as e:
            logger.error("[VIBE] Update failed: %s", e, exc_info=True)
            return OperationResult(success=False, error=str(e))
    
    async def delete_project(self, project_id: int, user_id: int) -> OperationResult:
        """Soft delete a project by archiving it."""
        try:
            await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        try:
            result = await db.execute(
                """
                UPDATE vibe_projects
                SET status = $1, updated_at = NOW()
                WHERE project_id = $2 AND user_id = $3
                """,
                ProjectStatus.ARCHIVED.value, project_id, user_id
            )
            
            # Check for successful update - handle different result formats
            success = result is not None and (
                result == "UPDATE 1" or 
                (isinstance(result, str) and result.startswith("UPDATE")) or
                result is True
            )
            
            if not success:
                logger.warning("[VIBE] delete_project unexpected result: %s", result)
            
            return OperationResult(
                success=True,  # If we got here without exception, consider it success
                data={"message": "Project archived"}
            )
        except Exception as e:
            logger.error("[VIBE] delete_project failed: %s", e, exc_info=True)
            return OperationResult(success=False, error=f"Archive failed: {e}")
    
    # ========================================================================
    # BUILD PIPELINE
    # ========================================================================
    
    async def run_intake(
        self,
        project_id: int,
        user_id: int,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> OperationResult:
        """
        Run intake conversation to gather project requirements.
        
        Args:
            project_id: Target project
            user_id: User ID
            user_message: User's message
            conversation_history: Previous conversation turns
            
        Returns:
            OperationResult with response and optional extracted brief
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate status - intake can only run in INTAKE status
        try:
            self._validate_status_for_operation(
                project, 
                [ProjectStatus.INTAKE],
                "Intake"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Build messages
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})
        
        # Feature flag for tool-enabled intake
        USE_INTAKE_TOOLS = True  # Enabled - Cloudinary + Brave Search configured
        
        response = None
        tool_uses = []
        
        if USE_INTAKE_TOOLS:
            # Create tool executor for this project with real-time activity logging
            async def tool_executor(tool_name: str, tool_input: Dict[str, Any]) -> str:
                """Execute Vibe tools and return results with activity logging."""
                # Log tool start with user-friendly descriptions
                tool_descriptions = {
                    "web_search": f"🔍 Searching: {tool_input.get('query', 'web')}...",
                    "screenshot_website": f"📸 Capturing screenshot: {tool_input.get('url', '')}...",
                    "save_inspiration": f"💾 Saving inspiration: {tool_input.get('description', '')}...",
                    "deep_research": f"🔬 Deep research: {tool_input.get('query', 'topic')}...",
                    "memory_search": f"🧠 Searching memories: {tool_input.get('query', '')}...",
                }
                activity_desc = tool_descriptions.get(tool_name, f"🔧 Using tool: {tool_name}")
                
                # Log activity for real-time UI feedback
                await self._log_activity(
                    project_id=project_id,
                    activity_type=ActivityType.INTAKE_MESSAGE,
                    description=activity_desc,
                    agent_name="Nicole",
                    metadata={"tool": tool_name, "status": "started"}
                )
                
                result = await self._execute_vibe_tool(tool_name, tool_input, project_id)
                
                # Log completion
                success = result.get("success", False) if isinstance(result, dict) else True
                await self._log_activity(
                    project_id=project_id,
                    activity_type=ActivityType.INTAKE_MESSAGE,
                    description=f"{'✅' if success else '⚠️'} {tool_name} complete",
                    agent_name="Nicole",
                    metadata={"tool": tool_name, "status": "complete", "success": success}
                )
                
                return json.dumps(result, default=str)
            
            # Try tool-enabled call, fall back to simple if it fails
            try:
                response, tool_uses = await claude_client.generate_response_with_tools(
                    messages=messages,
                    tools=VIBE_INTAKE_TOOLS,
                    tool_executor=tool_executor,
                    system_prompt=INTAKE_SYSTEM_PROMPT,
                    model=self.SONNET_MODEL,
                    max_tokens=3000,
                    temperature=0.7,
                    max_tool_iterations=5
                )
                
                # Log tool usage if any
                if tool_uses:
                    logger.info("[VIBE] Intake used %d tools: %s", 
                               len(tool_uses), 
                               [t.get("name") for t in tool_uses])
                    await self._log_activity(
                        project_id=project_id,
                        activity_type=ActivityType.INTAKE_MESSAGE,
                        description=f"Nicole used {len(tool_uses)} research tools",
                        agent_name="Nicole",
                        metadata={"tools_used": [t.get("name") for t in tool_uses]}
                    )
                    
            except Exception as e:
                logger.warning("[VIBE] Tool-enabled intake failed, falling back to simple: %s", e)
                response = None  # Fall through to simple mode
        
        # Simple mode (no tools) - more reliable for initial launch
        if response is None:
            try:
                response = await claude_client.generate_response(
                    messages=messages,
                    system_prompt=INTAKE_SYSTEM_PROMPT,
                    model=self.SONNET_MODEL,
                    max_tokens=2000,
                    temperature=0.7
                )
            except Exception as e:
                logger.error("[VIBE] Intake Claude call failed: %s", e, exc_info=True)
                return OperationResult(success=False, error=f"AI service error: {e}")
        
        # Estimate cost (rough: ~500 input, ~1000 output tokens)
        cost = estimate_api_cost(self.SONNET_MODEL, 500, 1000)
        await self._update_api_cost(project_id, user_id, cost)
        
        # Clean response of any XML hallucinations (Claude sometimes outputs fake function calls)
        import re
        response = re.sub(r'<function_calls>.*?</function_calls>', '', response, flags=re.DOTALL)
        response = re.sub(r'<invoke\s+name="[^"]*">.*?</invoke>', '', response, flags=re.DOTALL)
        response = re.sub(r'<parameter\s+name="[^"]*">.*?</parameter>', '', response, flags=re.DOTALL)
        response = response.strip()
        
        # Check if response contains a JSON brief
        brief = extract_json_from_response(response)
        new_status = ProjectStatus.INTAKE.value
        
        # Log the intake message
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.INTAKE_MESSAGE,
            description=f"Intake message received ({len(user_message)} chars)",
            user_id=user_id,
            agent_name="Nicole",
            metadata={"message_preview": user_message[:100]}
        )
        
        if brief:
            # Validate brief has required fields
            required_fields = ["business_name", "project_type"]
            if all(brief.get(f) for f in required_fields):
                # Save brief and advance status atomically
                try:
                    async with db.transaction() as conn:
                        await conn.execute(
                            """
                            UPDATE vibe_projects
                            SET brief = $1::jsonb, status = $2, updated_at = NOW()
                            WHERE project_id = $3 AND user_id = $4
                            """,
                            json.dumps(brief), ProjectStatus.PLANNING.value,
                            project_id, user_id
                        )
                    new_status = ProjectStatus.PLANNING.value
                    logger.info("[VIBE] Extracted brief for project %d", project_id)
                except Exception as e:
                    logger.error("[VIBE] Failed to save brief: %s", e, exc_info=True)
                    return OperationResult(
                        success=False,
                        error=f"Failed to save project brief: {e}",
                        api_cost=cost
                    )
                
                # Log brief extraction (non-critical, outside transaction)
                await self._log_activity(
                    project_id=project_id,
                    activity_type=ActivityType.BRIEF_EXTRACTED,
                    description=f"Project brief extracted for {brief.get('business_name', 'Unknown')}",
                    user_id=user_id,
                    agent_name="Nicole",
                    metadata={"business_name": brief.get("business_name"), "project_type": brief.get("project_type")}
                )
            else:
                logger.warning("[VIBE] Extracted JSON missing required fields")
                brief = None
        
        return OperationResult(
            success=True,
            data={
                "response": response,
                "brief": brief,
                "status": new_status,
                "brief_complete": brief is not None
            },
            api_cost=cost
        )
    
    async def run_architecture(
        self,
        project_id: int,
        user_id: int
    ) -> OperationResult:
        """
        Generate architecture specification using Opus.
        
        Requires project to be in PLANNING status with a completed brief.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate status
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.PLANNING],
                "Architecture planning"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate brief exists
        raw_brief = project.get("brief")
        logger.info(f"[VIBE] Project {project_id} raw brief type: {type(raw_brief).__name__}, value preview: {str(raw_brief)[:200] if raw_brief else 'None'}")
        
        brief = raw_brief if raw_brief else {}
        # Handle case where brief might be a JSON string
        if isinstance(brief, str):
            try:
                brief = json.loads(brief)
            except (json.JSONDecodeError, TypeError):
                brief = {}
        
        if not brief or not isinstance(brief, dict) or not brief.get("business_name"):
            logger.warning(f"[VIBE] Project {project_id} brief validation failed: brief={type(brief).__name__}, keys={brief.keys() if isinstance(brief, dict) else 'N/A'}")
            return OperationResult(
                success=False,
                error="Project has no brief. Complete intake first."
            )
        
        # Log planning start for progress tracking
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.INTAKE_MESSAGE,
            description="🏗️ Starting architecture design...",
            user_id=user_id,
            agent_name="Orchestrator",
            metadata={"phase": "planning", "step": "started"}
        )
        
        # Step 1: Use Gemini for design research (if available)
        from app.services.model_orchestrator import model_orchestrator
        
        design_system = None
        try:
            await self._log_activity(
                project_id=project_id,
                activity_type=ActivityType.INTAKE_MESSAGE,
                description="🎨 Design Agent is researching design trends...",
                user_id=user_id,
                agent_name="Design Agent",
                metadata={"phase": "planning", "step": "design_research"}
            )
            
            # Log what we're searching for
            business_type = brief.get("business_type", brief.get("project_type", "business"))
            await self._log_agent_message(
                project_id=project_id,
                agent_name="Design Agent",
                message_type="thinking",
                content=f"Researching current design trends for {business_type} websites. Looking for color palettes, typography, and layout patterns that match the brand feel: {brief.get('brand_feel', 'professional')}",
                user_id=user_id
            )
            
            design_system = await model_orchestrator.generate_design_system(brief, project_id)
            
            if design_system.generated_by == "gemini":
                logger.info("[VIBE] Design system generated by Gemini with trends: %s", 
                           design_system.trends_applied)
                
                # Log the design system details
                await self._log_agent_message(
                    project_id=project_id,
                    agent_name="Design Agent",
                    message_type="response",
                    content=f"Design system created:\n• Primary: {design_system.colors.get('primary', 'N/A')}\n• Secondary: {design_system.colors.get('secondary', 'N/A')}\n• Fonts: {design_system.typography.get('heading_font', 'N/A')} / {design_system.typography.get('body_font', 'N/A')}\n• Style: {design_system.inspiration_notes[:100] if design_system.inspiration_notes else 'Modern professional'}",
                    user_id=user_id
                )
                
                await self._log_activity(
                    project_id=project_id,
                    activity_type=ActivityType.INTAKE_MESSAGE,
                    description=f"✨ Design system ready - using {', '.join(design_system.trends_applied[:2]) if design_system.trends_applied else 'modern'} trends",
                    user_id=user_id,
                    agent_name="Design Agent",
                    metadata={"phase": "planning", "step": "design_complete", "generated_by": "gemini"}
                )
        except Exception as e:
            logger.warning("[VIBE] Gemini design research failed, Claude will handle design: %s", e)
            await self._log_agent_message(
                project_id=project_id,
                agent_name="Design Agent",
                message_type="error",
                content=f"Design research encountered an issue: {str(e)[:100]}. Falling back to Architect Agent for design.",
                user_id=user_id
            )
        
        # Step 2: Call Claude Opus for architecture (with design system from Gemini)
        try:
            await self._log_activity(
                project_id=project_id,
                activity_type=ActivityType.INTAKE_MESSAGE,
                description="🏗️ Architect Agent is designing the site structure...",
                user_id=user_id,
                agent_name="Architect Agent",
                metadata={"phase": "planning", "step": "claude_call"}
            )
            
            # Log what the Architect is thinking
            await self._log_agent_message(
                project_id=project_id,
                agent_name="Architect Agent",
                message_type="thinking",
                content=f"Analyzing brief for {brief.get('business_name', 'project')}. Planning page structure, component hierarchy, and SEO strategy...",
                user_id=user_id
            )
            
            # Include design system in the architecture prompt if available
            design_context = ""
            if design_system:
                design_context = f"""
## Pre-Researched Design System (from Design Agent)
Use these design tokens exactly:

Colors:
{json.dumps(design_system.colors, indent=2)}

Typography:
{json.dumps(design_system.typography, indent=2)}

Style Notes: {design_system.inspiration_notes}

"""
                await self._log_agent_message(
                    project_id=project_id,
                    agent_name="Architect Agent",
                    message_type="prompt",
                    content=f"Received design system from Design Agent. Integrating colors ({design_system.colors.get('primary', 'N/A')}) and typography ({design_system.typography.get('heading_font', 'N/A')}) into architecture spec...",
                    user_id=user_id
                )
            
            response = await self._call_claude_with_retry(
                messages=[{
                    "role": "user",
                    "content": f"{design_context}Create a detailed architecture specification for this project:\n\n{json.dumps(brief, indent=2)}"
                }],
                system_prompt=ARCHITECT_AGENT_PROMPT,
                model=self.OPUS_MODEL,
                max_tokens=4000,
                temperature=0.5,
                max_retries=3,
                base_delay=2.0
            )
            
            # Log response preview
            architecture_preview = extract_json_from_response(response)
            if architecture_preview:
                pages = architecture_preview.get("pages", [])
                components = architecture_preview.get("components", [])
                await self._log_agent_message(
                    project_id=project_id,
                    agent_name="Architect Agent",
                    message_type="response",
                    content=f"Architecture designed:\n• {len(pages)} pages: {', '.join(p.get('name', 'Page') for p in pages[:5])}\n• {len(components)} components planned\n• SEO: {architecture_preview.get('seo', {}).get('title', 'N/A')[:50]}",
                    user_id=user_id
                )
                
        except Exception as e:
            logger.error("[VIBE] Architecture Claude call failed after retries: %s", e, exc_info=True)
            await self._log_agent_message(
                project_id=project_id,
                agent_name="Architect Agent",
                message_type="error",
                content=f"Architecture generation failed: {str(e)[:100]}",
                user_id=user_id
            )
            return OperationResult(success=False, error=f"AI service error: {e}")
        
        # Estimate cost (Opus: ~1000 input, ~2000 output)
        cost = estimate_api_cost(self.OPUS_MODEL, 1000, 2000)
        await self._update_api_cost(project_id, user_id, cost)
        
        # Extract architecture JSON
        architecture = extract_json_from_response(response)
        
        # Merge Gemini's design system into the architecture (if available)
        if architecture and design_system:
            if "design_system" not in architecture:
                architecture["design_system"] = {}
            
            # Gemini's design takes precedence as it's based on real-time research
            if design_system.colors:
                architecture["design_system"]["colors"] = design_system.colors
            if design_system.typography:
                architecture["design_system"]["typography"] = design_system.typography
            if design_system.spacing:
                architecture["design_system"]["spacing"] = design_system.spacing
            
            # Add provenance info
            architecture["design_system"]["generated_by"] = design_system.generated_by
            if design_system.trends_applied:
                architecture["design_system"]["trends"] = design_system.trends_applied
        
        if architecture and architecture.get("pages"):
            # Valid architecture - advance status atomically
            page_count = len(architecture.get("pages", []))
            
            try:
                async with db.transaction() as conn:
                    await conn.execute(
                        """
                        UPDATE vibe_projects
                        SET architecture = $1::jsonb, status = $2, updated_at = NOW()
                        WHERE project_id = $3 AND user_id = $4
                        """,
                        json.dumps(architecture), ProjectStatus.BUILDING.value,
                        project_id, user_id
                    )
                logger.info("[VIBE] Generated architecture for project %d with %d pages",
                           project_id, page_count)
            except Exception as e:
                logger.error("[VIBE] Failed to save architecture: %s", e, exc_info=True)
                return OperationResult(
                    success=False,
                    error=f"Failed to save architecture: {e}",
                    api_cost=cost
                )
            
            # Log activity (non-critical, outside transaction)
            await self._log_activity(
                project_id=project_id,
                activity_type=ActivityType.ARCHITECTURE_GENERATED,
                description=f"Architecture generated with {page_count} pages",
                user_id=user_id,
                agent_name="Architect Agent",
                metadata={"page_count": page_count, "complexity": architecture.get("complexity")}
            )
            
            return OperationResult(
                success=True,
                data={
                    "architecture": architecture,
                    "status": ProjectStatus.BUILDING.value,
                    "page_count": page_count
                },
                api_cost=cost
            )
        else:
            logger.warning("[VIBE] Failed to extract valid architecture JSON")
            return OperationResult(
                success=False,
                error="Failed to generate valid architecture. Please try again.",
                data={"raw_response": response[:500]},
                api_cost=cost
            )
    
    async def run_build(
        self,
        project_id: int,
        user_id: int
    ) -> OperationResult:
        """
        Run the build phase - generate all code files.
        
        Uses Sonnet for code generation. Files are saved atomically.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate status
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.BUILDING],
                "Build"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate architecture exists - handle JSON string from database
        architecture = project.get("architecture", {})
        if isinstance(architecture, str):
            try:
                architecture = json.loads(architecture)
            except (json.JSONDecodeError, TypeError):
                architecture = {}
        
        brief = project.get("brief", {})
        if isinstance(brief, str):
            try:
                brief = json.loads(brief)
            except (json.JSONDecodeError, TypeError):
                brief = {}
        
        if not architecture or not architecture.get("pages"):
            return OperationResult(
                success=False,
                error="Project has no architecture. Run planning first."
            )
        
        # Log build start with progress tracking
        page_count = len(architecture.get("pages", []))
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.BUILD_STARTED,
            description=f"💻 Coding Agent starting code generation ({page_count} pages)...",
            user_id=user_id,
            agent_name="Coding Agent",
            metadata={"page_count": page_count, "phase": "build", "step": "started"}
        )
        
        # Build comprehensive prompt
        # Extract design system for clearer reference
        design = architecture.get("design_system", architecture.get("design", {}))
        colors = design.get("colors", {})
        typography = design.get("typography", {})
        content = architecture.get("content", {})
        
        build_prompt = f"""Build a complete Next.js 14 website. Generate ALL files in order.

## Client: {content.get('business_name', brief.get('business_name', 'Client'))}
{brief.get('description', '')}

## Design System (USE THESE EXACTLY)
**Colors:**
- Primary: {colors.get('primary', '#8B9D83')}
- Secondary: {colors.get('secondary', '#F4E4BC')}
- Accent: {colors.get('accent', '#D4A574')}

**Typography:**
- Heading: {typography.get('heading_font', 'Playfair Display')}
- Body: {typography.get('body_font', 'Source Sans Pro')}

## Architecture
{json.dumps(architecture, indent=2)}

## GENERATION ORDER (Follow exactly)

### Step 1: tailwind.config.ts
Configure theme with brand colors as custom values (sage, cream, warm-brown, etc.)

### Step 2: app/globals.css
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {{
  --primary: {colors.get('primary', '#8B9D83')};
  --secondary: {colors.get('secondary', '#F4E4BC')};
  --accent: {colors.get('accent', '#D4A574')};
}}
```
Plus utility classes for buttons, sections, typography.

### Step 3: components/Header.tsx
Navigation with logo, links, mobile menu, CTA

### Step 4: components/Footer.tsx
Footer with contact info, links, social icons

### Step 5: Each component from architecture
Generate complete components with:
- TypeScript interfaces for props
- Semantic HTML structure
- Tailwind classes using the brand colors
- Real content from the brief

### Step 6: app/layout.tsx
Root layout importing Header, Footer, fonts

### Step 7: app/page.tsx
Homepage composing all components

## Content to Use
Business: {content.get('business_name', brief.get('business_name', 'Business'))}
Location: {content.get('address', brief.get('location', 'NJ'))}
Phone: {content.get('phone', '')}
Email: {content.get('email', '')}

Generate COMPLETE code for each file. No abbreviations."""

        try:
            # Log that we're generating code
            await self._log_activity(
                project_id=project_id,
                activity_type=ActivityType.BUILD_STARTED,
                description="💻 Coding Agent is generating code files...",
                user_id=user_id,
                agent_name="Coding Agent",
                metadata={"phase": "build", "step": "claude_call"}
            )
            
            # Log the prompt being sent (for visibility)
            await self._log_agent_message(
                project_id=project_id,
                agent_name="Coding Agent",
                message_type="prompt",
                content=f"Generating code for {page_count} pages with {len(architecture.get('components', []))} components...",
                user_id=user_id
            )
            
            response = await self._call_claude_with_retry(
                messages=[{"role": "user", "content": build_prompt}],
                system_prompt=CODING_AGENT_PROMPT,
                model=self.SONNET_MODEL,
                max_tokens=16000,  # Large budget for code generation
                temperature=0.3,   # Lower temperature for code
                max_retries=3,
                base_delay=2.0     # Longer delay for large generations
            )
            
            # Log the response summary (for visibility)
            files_preview = parse_files_from_response(response[:5000])  # Quick preview
            await self._log_agent_message(
                project_id=project_id,
                agent_name="Coding Agent",
                message_type="response",
                content=f"Generated {len(files_preview)} files so far: {', '.join(f.path for f in files_preview[:5])}{'...' if len(files_preview) > 5 else ''}",
                user_id=user_id
            )
            
            # Log completion
            await self._log_activity(
                project_id=project_id,
                activity_type=ActivityType.BUILD_STARTED,
                description="📝 Coding Agent parsing generated files...",
                user_id=user_id,
                agent_name="Coding Agent",
                metadata={"phase": "build", "step": "parsing"}
            )
        except Exception as e:
            logger.error("[VIBE] Build Claude call failed after retries: %s", e, exc_info=True)
            return OperationResult(success=False, error=f"AI service error: {e}")
        
        # Estimate cost (large generation: ~2000 input, ~8000 output)
        cost = estimate_api_cost(self.SONNET_MODEL, 2000, 8000)
        await self._update_api_cost(project_id, user_id, cost)
        
        # Parse files from response
        files = parse_files_from_response(response)
        
        if not files:
            return OperationResult(
                success=False,
                error="No files could be parsed from the build output. Please retry.",
                data={"raw_response_preview": response[:1000]},
                api_cost=cost
            )
        
        # Save files and update status atomically within a transaction
        # Use optimistic locking: verify status hasn't changed since we started
        preview_url = f"https://preview.alphawave.ai/p/{project_id}"
        try:
            async with db.transaction() as conn:
                # Save all files within the transaction
                file_count = await self._save_files_batch(
                    project_id, files,
                    user_id=user_id,
                    agent_name="Coding Agent",
                    conn=conn
                )
                
                # Update project status with optimistic locking
                # Only update if status is still BUILDING (no concurrent modification)
                result = await conn.execute(
                    """
                    UPDATE vibe_projects
                    SET status = $1, preview_url = $2, updated_at = NOW()
                    WHERE project_id = $3 AND user_id = $4 AND status = $5
                    """,
                    ProjectStatus.QA.value, preview_url, project_id, user_id,
                    ProjectStatus.BUILDING.value
                )
                
                # Check if update succeeded (optimistic lock validation)
                if result and "UPDATE 0" in result:
                    raise ConcurrencyError(
                        "Project was modified by another process. Please refresh and try again."
                    )
        except ConcurrencyError as e:
            logger.warning("[VIBE] Build concurrency conflict: %s", e)
            return OperationResult(
                success=False,
                error=str(e),
                api_cost=cost
            )
        except Exception as e:
            logger.error("[VIBE] Build transaction failed: %s", e, exc_info=True)
            return OperationResult(
                success=False,
                error=f"Failed to save build output: {e}",
                api_cost=cost
            )
        
        # Log build completion (outside transaction - non-critical)
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.BUILD_COMPLETED,
            description=f"💻 Coding Agent completed: {file_count} files generated",
            user_id=user_id,
            agent_name="Coding Agent",
            metadata={"file_count": file_count, "files": [f.path for f in files[:10]]}
        )
        
        return OperationResult(
            success=True,
            data={
                "status": ProjectStatus.QA.value,
                "files_generated": [f.path for f in files],
                "file_count": file_count,
                "preview_url": preview_url
            },
            api_cost=cost
        )
    
    async def run_qa(
        self,
        project_id: int,
        user_id: int
    ) -> OperationResult:
        """
        Run QA checks on generated files.
        
        Analyzes code quality, accessibility, and correctness.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate status
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.QA],
                "QA"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Log QA start
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.INTAKE_MESSAGE,
            description="🔬 Starting QA review...",
            user_id=user_id,
            agent_name="QA Agent"
        )
        
        # Get files for review
        files = await self.get_project_files(project_id)
        
        if not files:
            return OperationResult(
                success=False,
                error="No files to review. Run build first."
            )
        
        # Log file analysis start
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.INTAKE_MESSAGE,
            description=f"📂 Analyzing {len(files)} files for quality issues...",
            user_id=user_id,
            agent_name="QA Agent"
        )
        
        # Build file summary for QA
        file_summaries = []
        for f in files[:15]:  # Limit to 15 files for context
            content = f['content']
            if len(content) > 3000:
                content = content[:3000] + "\n... [truncated]"
            file_summaries.append(f"=== {f['file_path']} ===\n{content}")
        
        qa_prompt = f"""Review this Next.js/TypeScript codebase for production readiness:

{chr(10).join(file_summaries)}

Total files: {len(files)}

Perform a comprehensive QA review and output your findings as JSON."""

        # Log AI review start
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.INTAKE_MESSAGE,
            description="🧠 Running AI code review...",
            user_id=user_id,
            agent_name="QA Agent"
        )
        
        try:
            response = await self._call_claude_with_retry(
                messages=[{"role": "user", "content": qa_prompt}],
                system_prompt=QA_AGENT_PROMPT,
                model=self.SONNET_MODEL,
                max_tokens=3000,
                temperature=0.3,
                max_retries=3,
                base_delay=1.5
            )
        except Exception as e:
            logger.error("[VIBE] QA Claude call failed after retries: %s", e, exc_info=True)
            return OperationResult(success=False, error=f"AI service error: {e}")
        
        # Estimate cost
        cost = estimate_api_cost(self.SONNET_MODEL, 3000, 1500)
        await self._update_api_cost(project_id, user_id, cost)
        
        # Parse QA result
        qa_result = extract_json_from_response(response)
        
        if not qa_result:
            qa_result = {
                "passed": True,
                "score": 75,
                "issues": [],
                "suggestions": ["Manual review recommended"],
                "summary": "Automated extraction failed - manual review needed"
            }
        
        # Determine pass/fail
        passed = qa_result.get("passed", False)
        score = qa_result.get("score", 0)
        
        # If score >= 70 and no critical issues, consider it passed
        critical_issues = [i for i in qa_result.get("issues", []) 
                         if isinstance(i, dict) and i.get("severity") == "critical"]
        
        if score >= 70 and not critical_issues:
            passed = True
        
        # Update status atomically with optimistic locking
        new_status = ProjectStatus.REVIEW.value if passed else ProjectStatus.QA.value
        try:
            async with db.transaction() as conn:
                result = await conn.execute(
                    """
                    UPDATE vibe_projects
                    SET status = $1, updated_at = NOW()
                    WHERE project_id = $2 AND user_id = $3 AND status = $4
                    """,
                    new_status, project_id, user_id, ProjectStatus.QA.value
                )
                if result and "UPDATE 0" in result:
                    raise ConcurrencyError("Project was modified. Please refresh and retry.")
        except ConcurrencyError:
            raise
        except Exception as e:
            logger.error("[VIBE] QA status update failed: %s", e, exc_info=True)
            return OperationResult(success=False, error=f"Failed to update status: {e}", api_cost=cost)
        
        # Log QA result
        issue_count = len(qa_result.get("issues", []))
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.QA_PASSED if passed else ActivityType.QA_FAILED,
            description=f"QA {'passed' if passed else 'failed'} - Score: {score}/100, {issue_count} issues",
            user_id=user_id,
            agent_name="QA Agent",
            metadata={"score": score, "passed": passed, "issue_count": issue_count}
        )
        
        return OperationResult(
            success=True,
            data={
                "status": new_status,
                "passed": passed,
                "score": score,
                "issues": qa_result.get("issues", []),
                "suggestions": qa_result.get("suggestions", []),
                "summary": qa_result.get("summary", ""),
                "needs_rebuild": not passed
            },
            api_cost=cost
        )
    
    async def run_review(
        self,
        project_id: int,
        user_id: int
    ) -> OperationResult:
        """
        Final review using Opus before client delivery.
        
        Comprehensive quality assessment and approval decision.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate status
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.REVIEW],
                "Final review"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Log review start
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.INTAKE_MESSAGE,
            description="✨ Starting final review with Opus...",
            user_id=user_id,
            agent_name="Review Agent"
        )
        
        brief = project.get("brief", {})
        if isinstance(brief, str):
            try:
                brief = json.loads(brief)
            except (json.JSONDecodeError, TypeError):
                brief = {}
        
        architecture = project.get("architecture", {})
        if isinstance(architecture, str):
            try:
                architecture = json.loads(architecture)
            except (json.JSONDecodeError, TypeError):
                architecture = {}
        
        files = await self.get_project_files(project_id)
        
        # Log file gathering
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.INTAKE_MESSAGE,
            description=f"📋 Reviewing {len(files)} files against requirements...",
            user_id=user_id,
            agent_name="Review Agent"
        )
        
        # Get sample file contents
        sample_files = []
        priority_files = ['layout.tsx', 'page.tsx', 'globals.css']
        
        for f in files:
            if any(p in f['file_path'] for p in priority_files):
                content = f['content'][:2000] if len(f['content']) > 2000 else f['content']
                sample_files.append(f"=== {f['file_path']} ===\n{content}")
        
        # Log AI review
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.INTAKE_MESSAGE,
            description="🧠 Opus is evaluating delivery readiness...",
            user_id=user_id,
            agent_name="Review Agent"
        )
        
        review_prompt = f"""Conduct a final comprehensive review of this AlphaWave project.

## Client Brief
{json.dumps(brief, indent=2)}

## Technical Architecture
{json.dumps(architecture, indent=2)}

## Generated Files ({len(files)} total)
{chr(10).join(sample_files[:5])}

## Review Task
Assess whether this project is ready for client delivery. Consider:
1. Does the implementation match all client requirements?
2. Is the code production-quality?
3. Would you be proud to deliver this to a paying client?

Output your comprehensive review as JSON."""

        try:
            response = await self._call_claude_with_retry(
                messages=[{"role": "user", "content": review_prompt}],
                system_prompt=REVIEW_AGENT_PROMPT,
                model=self.OPUS_MODEL,
                max_tokens=2500,
                temperature=0.3,
                max_retries=3,
                base_delay=2.0
            )
        except Exception as e:
            logger.error("[VIBE] Review Claude call failed after retries: %s", e, exc_info=True)
            return OperationResult(success=False, error=f"AI service error: {e}")
        
        # Estimate cost (Opus)
        cost = estimate_api_cost(self.OPUS_MODEL, 2000, 1500)
        await self._update_api_cost(project_id, user_id, cost)
        
        # Parse review result
        review_result = extract_json_from_response(response)
        
        if not review_result:
            review_result = {
                "approved": False,
                "score": 0,
                "recommendation": "revise",
                "concerns": ["Failed to parse review results"]
            }
        
        approved = review_result.get("approved", False)
        recommendation = review_result.get("recommendation", "revise")
        score = review_result.get("score", 0)
        
        # Update status atomically with optimistic locking
        if approved or recommendation == "approve":
            new_status = ProjectStatus.APPROVED.value
        else:
            new_status = ProjectStatus.REVIEW.value  # Stay in review until fixed
        
        try:
            async with db.transaction() as conn:
                result = await conn.execute(
                    """
                    UPDATE vibe_projects
                    SET status = $1, updated_at = NOW()
                    WHERE project_id = $2 AND user_id = $3 AND status = $4
                    """,
                    new_status, project_id, user_id, ProjectStatus.REVIEW.value
                )
                if result and "UPDATE 0" in result:
                    raise ConcurrencyError("Project was modified. Please refresh and retry.")
        except ConcurrencyError:
            raise
        except Exception as e:
            logger.error("[VIBE] Review status update failed: %s", e, exc_info=True)
            return OperationResult(success=False, error=f"Failed to update status: {e}", api_cost=cost)
        
        # Log review result
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.REVIEW_APPROVED if approved else ActivityType.REVIEW_REJECTED,
            description=f"✨ Review Agent: {'Approved' if approved else 'Needs revision'} - Score: {score}/10",
            user_id=user_id,
            agent_name="Review Agent",
            metadata={"score": score, "recommendation": recommendation, "approved": approved}
        )
        
        return OperationResult(
            success=True,
            data={
                "status": new_status,
                "approved": approved,
                "score": score,
                "strengths": review_result.get("strengths", []),
                "concerns": review_result.get("concerns", []),
                "required_changes": review_result.get("required_changes"),
                "recommendation": recommendation,
                "client_ready": review_result.get("client_ready", False)
            },
            api_cost=cost
        )
    
    async def retry_phase(
        self,
        project_id: int,
        user_id: int,
        target_status: Optional[str] = None
    ) -> OperationResult:
        """
        Retry a stuck phase by keeping current status or optionally resetting.
        
        This allows re-running planning/build/qa for projects that got stuck.
        If target_status is provided, resets project to that status first.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        current_status = project.get("status", "intake")
        
        # Determine what to do
        if target_status:
            # Validate target_status is valid
            valid_statuses = ["planning", "building", "qa", "review"]
            if target_status not in valid_statuses:
                return OperationResult(
                    success=False,
                    error=f"Invalid target status. Must be one of: {valid_statuses}"
                )
            
            # Reset to target status
            try:
                await db.execute(
                    """
                    UPDATE vibe_projects
                    SET status = $1, updated_at = NOW()
                    WHERE project_id = $2 AND user_id = $3
                    """,
                    target_status, project_id, user_id
                )
                
                await self._log_activity(
                    project_id=project_id,
                    activity_type=ActivityType.INTAKE_MESSAGE,
                    description=f"🔄 Reset project to {target_status} phase for retry",
                    user_id=user_id,
                    agent_name="System",
                    metadata={"from_status": current_status, "to_status": target_status}
                )
                
                return OperationResult(
                    success=True,
                    data={
                        "status": target_status,
                        "message": f"Project reset to {target_status}. Ready to run pipeline."
                    }
                )
            except Exception as e:
                logger.error("[VIBE] Failed to reset project status: %s", e, exc_info=True)
                return OperationResult(success=False, error=f"Failed to reset: {e}")
        else:
            # Just log that we're retrying (frontend will call the appropriate run_* method)
            await self._log_activity(
                project_id=project_id,
                activity_type=ActivityType.INTAKE_MESSAGE,
                description=f"🔄 Retrying {current_status} phase...",
                user_id=user_id,
                agent_name="System",
                metadata={"status": current_status}
            )
            
            return OperationResult(
                success=True,
                data={
                    "status": current_status,
                    "message": f"Ready to retry {current_status} phase"
                }
            )
    
    async def approve_project(
        self,
        project_id: int,
        user_id: int
    ) -> OperationResult:
        """
        Manual approval by Glen - marks project ready for deployment.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Can approve from REVIEW or APPROVED status
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.REVIEW, ProjectStatus.APPROVED],
                "Approval"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Atomically update status with optimistic locking
        previous_status = project.get("status")
        try:
            async with db.transaction() as conn:
                result = await conn.execute(
                    """
                    UPDATE vibe_projects
                    SET status = $1, updated_at = NOW()
                    WHERE project_id = $2 AND user_id = $3 AND status = $4
                    """,
                    ProjectStatus.APPROVED.value, project_id, user_id, previous_status
                )
                if result and "UPDATE 0" in result:
                    raise ConcurrencyError("Project was modified. Please refresh and retry.")
        except ConcurrencyError:
            raise
        except Exception as e:
            logger.error("[VIBE] Approval status update failed: %s", e, exc_info=True)
            return OperationResult(success=False, error=f"Failed to approve: {e}")
        
        logger.info("[VIBE] Project %d approved by user %d", project_id, user_id)
        
        # Log manual approval
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.MANUALLY_APPROVED,
            description="Project manually approved for deployment",
            user_id=user_id,
            metadata={"previous_status": previous_status}
        )
        
        return OperationResult(
            success=True,
            data={
                "status": ProjectStatus.APPROVED.value,
                "message": "Project approved and ready for deployment"
            }
        )
    
    async def deploy_project(
        self,
        project_id: int,
        user_id: int,
        preview_url: Optional[str] = None,
        production_url: Optional[str] = None
    ) -> OperationResult:
        """
        Deploy the project. Currently a placeholder that sets URLs and status.
        
        In production, this would integrate with GitHub and Vercel APIs.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Must be approved before deployment
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.APPROVED],
                "Deployment"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Generate URLs if not provided
        final_preview = preview_url or f"https://preview.alphawave.ai/p/{project_id}"
        final_production = production_url or f"https://sites.alphawave.ai/{project_id}"
        
        # Log deployment start
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.DEPLOYMENT_STARTED,
            description="Deployment initiated",
            user_id=user_id,
            metadata={"preview_url": final_preview}
        )
        
        # Atomically update status with optimistic locking
        try:
            async with db.transaction() as conn:
                result = await conn.execute(
                    """
                    UPDATE vibe_projects
                    SET status = $1, preview_url = $2, production_url = $3, updated_at = NOW()
                    WHERE project_id = $4 AND user_id = $5 AND status = $6
                    """,
                    ProjectStatus.DEPLOYED.value, final_preview, final_production,
                    project_id, user_id, ProjectStatus.APPROVED.value
                )
                if result and "UPDATE 0" in result:
                    raise ConcurrencyError("Project was modified. Please refresh and retry.")
        except ConcurrencyError:
            raise
        except Exception as e:
            logger.error("[VIBE] Deployment status update failed: %s", e, exc_info=True)
            return OperationResult(success=False, error=f"Failed to deploy: {e}")
        
        logger.info("[VIBE] Project %d deployed to %s", project_id, final_production)
        
        # Log deployment completion
        await self._log_activity(
            project_id=project_id,
            activity_type=ActivityType.DEPLOYMENT_COMPLETED,
            description=f"Deployed to {final_production}",
            user_id=user_id,
            metadata={
                "preview_url": final_preview,
                "production_url": final_production
            }
        )
        
        return OperationResult(
            success=True,
            data={
                "status": ProjectStatus.DEPLOYED.value,
                "preview_url": final_preview,
                "production_url": final_production,
                "message": "Project deployed successfully"
            }
        )
    
    # ========================================================================
    # FILE MANAGEMENT
    # ========================================================================
    
    async def get_project_files(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all files for a project."""
        results = await db.fetch(
            """
            SELECT file_id, file_path, content, created_at, updated_at
            FROM vibe_files
            WHERE project_id = $1
            ORDER BY file_path
            """,
            project_id
        )
        return [dict(r) for r in results] if results else []
    
    async def get_file(
        self, 
        project_id: int, 
        file_path: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific file by path."""
        result = await db.fetchrow(
            """
            SELECT file_id, file_path, content, created_at, updated_at
            FROM vibe_files
            WHERE project_id = $1 AND file_path = $2
            """,
            project_id, file_path
        )
        return dict(result) if result else None
    
    # ========================================================================
    # LESSONS LEARNING SYSTEM
    # ========================================================================
    
    async def capture_lesson(
        self,
        project_id: int,
        category: str,
        issue: str,
        solution: str,
        impact: str = "medium",
        tags: Optional[List[str]] = None
    ) -> OperationResult:
        """
        Capture a lesson learned from a project.
        
        Args:
            project_id: Source project
            category: LessonCategory value
            issue: What was the problem
            solution: How it was solved
            impact: high/medium/low
            tags: Searchable tags
            
        Returns:
            OperationResult with lesson ID
        """
        # Validate category
        try:
            LessonCategory(category)
        except ValueError:
            return OperationResult(
                success=False,
                error=f"Invalid category: {category}"
            )
        
        # Validate and sanitize tags
        MAX_TAGS = 10
        MAX_TAG_LENGTH = 50
        
        if tags:
            if len(tags) > MAX_TAGS:
                return OperationResult(
                    success=False,
                    error=f"Too many tags (max {MAX_TAGS}). Got {len(tags)}."
                )
            
            sanitized_tags = []
            for tag in tags:
                if not isinstance(tag, str):
                    continue
                tag = tag.strip().lower()
                if len(tag) > MAX_TAG_LENGTH:
                    tag = tag[:MAX_TAG_LENGTH]
                if tag:
                    sanitized_tags.append(tag)
            tags = sanitized_tags
        
        # Get project type (internal - no user access check for system operations)
        project = await self._get_project_internal(project_id)
        project_type = project.get("project_type", "website") if project else "website"
        
        # Generate embedding for semantic search
        lesson_text = f"{category}: {issue}. Solution: {solution}"
        embedding = await self._generate_embedding_safe(lesson_text)
        if embedding:
            logger.info("[VIBE] Generated embedding for lesson")
        else:
            logger.warning("[VIBE] Embedding unavailable, continuing without vector")
        
        try:
            if embedding:
                result = await db.fetchrow(
                    """
                    INSERT INTO vibe_lessons (
                        project_id, project_type, lesson_category,
                        issue, solution, impact, tags, embedding, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::vector, NOW())
                    RETURNING lesson_id
                    """,
                    project_id, project_type, category,
                    issue, solution, impact, tags or [], embedding
                )
            else:
                result = await db.fetchrow(
                    """
                    INSERT INTO vibe_lessons (
                        project_id, project_type, lesson_category,
                        issue, solution, impact, tags, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    RETURNING lesson_id
                    """,
                    project_id, project_type, category,
                    issue, solution, impact, tags or []
                )
            
            if result:
                logger.info("[VIBE] Captured lesson %d from project %d", 
                          result['lesson_id'], project_id)
                return OperationResult(
                    success=True,
                    data={"lesson_id": result['lesson_id'], "has_embedding": embedding is not None}
                )
            
            return OperationResult(success=False, error="Failed to save lesson")
            
        except Exception as e:
            logger.error("[VIBE] Failed to capture lesson: %s", e, exc_info=True)
            return OperationResult(success=False, error=str(e))
    
    async def get_relevant_lessons(
        self,
        project_type: str,
        category: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 10
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Get lessons relevant to a project type.
        
        Supports both category-based filtering and semantic search via embeddings.
        Returns (lessons, semantic_used_flag).
        """
        semantic_used = False
        
        # If query provided, try semantic search
        if query:
            try:
                query_embedding = await self._generate_embedding_safe(query)
                if query_embedding:
                    semantic_used = True
                    if category:
                        results = await db.fetch(
                            """
                            SELECT lesson_id, project_type, lesson_category,
                                   issue, solution, impact, times_applied,
                                   1 - (embedding <=> $1::vector) as similarity
                            FROM vibe_lessons
                            WHERE project_type = $2 
                              AND lesson_category = $3
                              AND embedding IS NOT NULL
                            ORDER BY embedding <=> $1::vector
                            LIMIT $4
                            """,
                            query_embedding, project_type, category, limit
                        )
                    else:
                        results = await db.fetch(
                            """
                            SELECT lesson_id, project_type, lesson_category,
                                   issue, solution, impact, times_applied,
                                   1 - (embedding <=> $1::vector) as similarity
                            FROM vibe_lessons
                            WHERE project_type = $2
                              AND embedding IS NOT NULL
                            ORDER BY embedding <=> $1::vector
                            LIMIT $3
                            """,
                            query_embedding, project_type, limit
                        )
                    
                    if results:
                        return [dict(r) for r in results], semantic_used
            except Exception as e:
                logger.warning("[VIBE] Semantic search failed, falling back: %s", e, exc_info=True)
                semantic_used = False
        
        # Fallback to category/popularity-based search
        if category:
            results = await db.fetch(
                """
                SELECT lesson_id, project_type, lesson_category,
                       issue, solution, impact, times_applied
                FROM vibe_lessons
                WHERE project_type = $1 AND lesson_category = $2
                ORDER BY times_applied DESC, created_at DESC
                LIMIT $3
                """,
                project_type, category, limit
            )
        else:
            results = await db.fetch(
                """
                SELECT lesson_id, project_type, lesson_category,
                       issue, solution, impact, times_applied
                FROM vibe_lessons
                WHERE project_type = $1
                ORDER BY times_applied DESC, created_at DESC
                LIMIT $2
                """,
                project_type, limit
            )
        
        return [dict(r) for r in results] if results else [], semantic_used

    async def backfill_lesson_embeddings(self, limit: int = 100) -> Dict[str, Any]:
        """
        Generate embeddings for lessons missing vectors.
        """
        rows = await db.fetch(
            """
            SELECT lesson_id, lesson_category, issue, solution
            FROM vibe_lessons
            WHERE embedding IS NULL
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit
        )
        updated = 0
        for row in rows or []:
            text = f"{row['lesson_category']}: {row['issue']}. Solution: {row['solution']}"
            embedding = await self._generate_embedding_safe(text)
            if not embedding:
                continue
            await db.execute(
                """
                UPDATE vibe_lessons
                SET embedding = $1::vector
                WHERE lesson_id = $2
                """,
                embedding, row["lesson_id"]
            )
            updated += 1
        return {"updated": updated, "remaining": max(0, (len(rows or []) - updated))}
    
    # ========================================================================
    # UI HELPERS
    # ========================================================================
    
    def get_agents_for_status(self, status: str) -> List[Dict[str, Any]]:
        """Get agent status configuration for UI display."""
        agents = [
            {"id": "intake", "name": "Intake", "icon": "📋", "status": "idle", "progress": 0, "task": "Gather requirements"},
            {"id": "planning", "name": "Planning", "icon": "🎯", "status": "idle", "progress": 0, "task": "Design architecture"},
            {"id": "build", "name": "Build", "icon": "🔨", "status": "idle", "progress": 0, "task": "Generate code"},
            {"id": "qa", "name": "QA", "icon": "🧪", "status": "idle", "progress": 0, "task": "Quality checks"},
            {"id": "review", "name": "Review", "icon": "✅", "status": "idle", "progress": 0, "task": "Final review"},
            {"id": "deploy", "name": "Deploy", "icon": "🚀", "status": "idle", "progress": 0, "task": "Ship to production"},
        ]
        
        status_to_index = {
            ProjectStatus.INTAKE.value: 0,
            ProjectStatus.PLANNING.value: 1,
            ProjectStatus.BUILDING.value: 2,
            ProjectStatus.QA.value: 3,
            ProjectStatus.REVIEW.value: 4,
            ProjectStatus.APPROVED.value: 5,
            ProjectStatus.DEPLOYING.value: 5,
            ProjectStatus.DEPLOYED.value: 6,
            ProjectStatus.DELIVERED.value: 6,
        }
        
        current_idx = status_to_index.get(status, 0)
        
        for i, agent in enumerate(agents):
            if i < current_idx:
                agent["status"] = "complete"
                agent["progress"] = 100
                agent["task"] = "Complete ✓"
            elif i == current_idx:
                agent["status"] = "working"
                agent["progress"] = 50
                agent["task"] = f"Working..."
        
        return agents
    
    def get_workflow_for_status(self, status: str) -> List[Dict[str, Any]]:
        """Get workflow steps for UI display."""
        workflow = [
            {"id": 1, "name": "Brief", "desc": "Gather requirements", "status": "pending"},
            {"id": 2, "name": "Plan", "desc": "Architecture design", "status": "pending"},
            {"id": 3, "name": "Build", "desc": "Generate code", "status": "pending"},
            {"id": 4, "name": "Test", "desc": "QA validation", "status": "pending"},
            {"id": 5, "name": "Ship", "desc": "Deploy live", "status": "pending"},
        ]
        
        status_to_step = {
            ProjectStatus.INTAKE.value: 1,
            ProjectStatus.PLANNING.value: 2,
            ProjectStatus.BUILDING.value: 3,
            ProjectStatus.QA.value: 4,
            ProjectStatus.REVIEW.value: 4,
            ProjectStatus.APPROVED.value: 5,
            ProjectStatus.DEPLOYING.value: 5,
            ProjectStatus.DEPLOYED.value: 6,
            ProjectStatus.DELIVERED.value: 6,
        }
        
        current_step = status_to_step.get(status, 1)
        
        for step in workflow:
            if step["id"] < current_step:
                step["status"] = "complete"
            elif step["id"] == current_step:
                step["status"] = "active"
        
        return workflow


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

vibe_service = VibeService()
