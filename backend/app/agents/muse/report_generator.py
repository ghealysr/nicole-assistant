"""
Muse Design Research Agent - Report Generator.

Generates comprehensive design reports, Cursor IDE prompts, and
ZIP export packages based on a Muse research session and approved style guide.

Anthropic Quality Standards:
- Clean async patterns
- Proper error handling
- Consistent database access via TigerDatabaseManager
- Structured logging
"""

import asyncio
import base64
import io
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zipfile import ZipFile, ZIP_DEFLATED

from app.agents.muse.constants import (
    CURSOR_PROMPT_MAX_TOKENS,
    CURSOR_PROMPT_TEMPERATURE,
    DESIGN_REPORT_MAX_TOKENS,
    DESIGN_REPORT_TEMPERATURE,
)
from app.agents.muse.prompts import (
    CURSOR_PROMPT_GENERATION_PROMPT,
    DESIGN_REPORT_GENERATION_PROMPT,
    MUSE_SYSTEM_PROMPT,
)
from app.database import db
from app.services.gemini_client import GEMINI_PRO, gemini_client
from app.services.knowledge_base_service import kb_service

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class GeneratedReport:
    """Result of report generation."""
    report_type: str
    title: str
    content_markdown: str
    word_count: int
    generation_model: str
    generation_tokens: int = 0
    generation_duration_ms: int = 0


@dataclass
class ExportPackage:
    """Result of export package generation."""
    package_name: str
    package_format: str
    size_bytes: int
    contents_manifest: Dict[str, Any]
    zip_data: bytes


# ============================================================================
# REPORT GENERATOR
# ============================================================================

class MuseReportGenerator:
    """
    Generates comprehensive design documentation from Muse research sessions.
    
    This service transforms raw research data into polished, actionable
    documentation suitable for stakeholders and AI coding assistants.
    
    Anthropic Quality:
    - Uses gemini_client.generate() for LLM calls
    - Uses db.fetchrow/fetch/fetchval for database queries
    - Proper async/await patterns throughout
    - Comprehensive error handling
    """
    
    def __init__(self):
        self.gemini = gemini_client
        self.kb = kb_service
    
    async def _get_session_data(self, session_id: int) -> Dict[str, Any]:
        """
        Fetches all relevant data for a given session.
        
        Returns:
            Dict containing session, style_guide, moodboards, and inspirations
        """
        # Fetch session with project info
        session = await db.fetchrow(
            """
            SELECT
                mrs.*,
                ep.name as project_name,
                ep.description as project_description
            FROM muse_research_sessions mrs
            JOIN enjineer_projects ep ON mrs.project_id = ep.id
            WHERE mrs.id = $1
            """,
            session_id
        )
        if not session:
            raise ValueError(f"Research session {session_id} not found.")

        # Fetch style guide if approved
        style_guide = None
        if session.get("approved_style_guide_id"):
            style_guide = await db.fetchrow(
                "SELECT * FROM muse_style_guides WHERE id = $1",
                session["approved_style_guide_id"]
            )

        # Fetch moodboards
        moodboards = await db.fetch(
            "SELECT * FROM muse_moodboards WHERE session_id = $1 ORDER BY option_number",
            session_id
        )

        # Fetch inspirations
        inspirations = await db.fetch(
            "SELECT * FROM muse_inspiration_inputs WHERE session_id = $1 ORDER BY created_at",
            session_id
        )

        return {
            "session": dict(session),
            "style_guide": dict(style_guide) if style_guide else None,
            "moodboards": [dict(mb) for mb in moodboards],
            "inspirations": [dict(insp) for insp in inspirations],
        }

    async def _get_knowledge_context(self, query: str, limit: int = 5) -> str:
        """Retrieves relevant knowledge base context."""
        try:
            context_sections = await self.kb.get_relevant_context(
                query=query,
                limit=limit,
                min_tokens=50,
                max_tokens=500
            )
            return "\n\n".join([s.content for s in context_sections])
        except Exception as e:
            logger.warning(f"[MUSE Report] KB context retrieval failed: {e}")
            return ""

    async def generate_design_report(
        self,
        session_id: int,
        project_id: Optional[int] = None  # Optional, for backwards compat
    ) -> GeneratedReport:
        """
        Generates a comprehensive design report in Markdown format.
        
        Args:
            session_id: The research session ID
            project_id: Optional project ID (not used, fetched from session)
            
        Returns:
            GeneratedReport with title, content, and metrics
        """
        start_time = datetime.now(timezone.utc)
        
        data = await self._get_session_data(session_id)
        session = data["session"]
        style_guide = data["style_guide"]

        if not style_guide:
            raise ValueError(f"No approved style guide found for session {session_id}.")

        # Parse JSON fields from session
        brief_analysis = json.loads(session["brief_analysis"]) if session.get("brief_analysis") else {}
        inspiration_analysis = json.loads(session["inspiration_analysis"]) if session.get("inspiration_analysis") else {}
        web_research_summary = json.loads(session["web_research_summary"]) if session.get("web_research_summary") else {}

        # Build context for LLM
        context_data = {
            "project_name": session["project_name"],
            "project_description": session["project_description"],
            "design_brief": session["design_brief"],
            "target_audience": session.get("target_audience"),
            "brand_keywords": session.get("brand_keywords"),
            "aesthetic_preferences": session.get("aesthetic_preferences"),
            "anti_patterns": session.get("anti_patterns"),
            "brief_analysis": brief_analysis,
            "inspiration_analysis": inspiration_analysis,
            "web_research_summary": web_research_summary,
            "selected_moodboard": next(
                (mb for mb in data["moodboards"] if mb["id"] == session.get("selected_moodboard_id")), 
                None
            ),
            "approved_style_guide": style_guide,
        }
        
        # Fetch relevant KB context
        kb_query = f"{session['project_name']} {session['design_brief']} design report"
        kb_context = await self._get_knowledge_context(kb_query)

        # Build prompt
        prompt = f"""
{MUSE_SYSTEM_PROMPT}

## Knowledge Base Context
{kb_context}

{DESIGN_REPORT_GENERATION_PROMPT}

## Session Data
```json
{json.dumps(context_data, indent=2, default=str)}
```

Please generate a comprehensive design report in Markdown format. 
Focus on explaining the 'why' behind design decisions, linking them back to the brief and research findings.
Make it professional and suitable for client presentation.
"""

        logger.info(f"[MUSE Report] Generating design report for session {session_id}...")
        
        # Generate using Gemini
        response = await self.gemini.generate(
            prompt=prompt,
            model=GEMINI_PRO,
            max_tokens=DESIGN_REPORT_MAX_TOKENS,
            temperature=DESIGN_REPORT_TEMPERATURE
        )
        
        report_content = response.text
        word_count = len(report_content.split())

        # Store the report
        try:
            report_id = await db.fetchval(
                """
                INSERT INTO muse_reports (session_id, style_guide_id, report_type, report_content, format)
                VALUES ($1, $2, 'design_report', $3, 'markdown')
                RETURNING id
                """,
                session_id,
                style_guide["id"],
                report_content
            )
            logger.info(f"[MUSE Report] Design report {report_id} stored for session {session_id}")
        except Exception as e:
            logger.warning(f"[MUSE Report] Failed to store report: {e}")
            report_id = None

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        return GeneratedReport(
            report_type="design_report",
            title=f"Design Report: {session['project_name']}",
            content_markdown=report_content,
            word_count=word_count,
            generation_model=response.model,
            generation_tokens=response.total_tokens,
            generation_duration_ms=duration_ms
        )

    async def generate_cursor_prompt(
        self,
        session_id: int,
        project_id: Optional[int] = None  # Optional, for backwards compat
    ) -> GeneratedReport:
        """
        Generates a detailed Cursor IDE prompt for implementation.
        
        This prompt guides AI coding assistants to build the project
        according to the approved design specification.
        
        Args:
            session_id: The research session ID
            project_id: Optional project ID (not used, fetched from session)
            
        Returns:
            GeneratedReport ready for Cursor IDE
        """
        start_time = datetime.now(timezone.utc)
        
        data = await self._get_session_data(session_id)
        session = data["session"]
        style_guide = data["style_guide"]

        if not style_guide:
            raise ValueError(f"No approved style guide found for session {session_id}.")

        # Parse JSON fields
        brief_analysis = json.loads(session["brief_analysis"]) if session.get("brief_analysis") else {}
        
        # Build context
        context_data = {
            "project_name": session["project_name"],
            "project_description": session["project_description"],
            "design_brief": session["design_brief"],
            "target_audience": session.get("target_audience"),
            "brand_keywords": session.get("brand_keywords"),
            "aesthetic_preferences": session.get("aesthetic_preferences"),
            "anti_patterns": session.get("anti_patterns"),
            "brief_analysis": brief_analysis,
            "selected_moodboard": next(
                (mb for mb in data["moodboards"] if mb["id"] == session.get("selected_moodboard_id")), 
                None
            ),
            "approved_style_guide": style_guide,
        }
        
        # KB context for coding best practices
        kb_query = "coding best practices, design systems, component architecture"
        kb_context = await self._get_knowledge_context(kb_query)

        # Build prompt
        prompt = f"""
{MUSE_SYSTEM_PROMPT}

## Knowledge Base Context for Implementation
{kb_context}

{CURSOR_PROMPT_GENERATION_PROMPT}

## Session Data
```json
{json.dumps(context_data, indent=2, default=str)}
```

Generate a detailed Cursor IDE prompt that guides the AI to build this project.
Include specific instructions for:
- Component structure and naming
- Tailwind CSS styling with the approved design tokens
- Responsive breakpoints
- Animations and interactions
- Accessibility requirements

The output should be a Markdown document ready for Nicole's planning phase.
"""

        logger.info(f"[MUSE Report] Generating Cursor prompt for session {session_id}...")
        
        response = await self.gemini.generate(
            prompt=prompt,
            model=GEMINI_PRO,
            max_tokens=CURSOR_PROMPT_MAX_TOKENS,
            temperature=CURSOR_PROMPT_TEMPERATURE
        )
        
        prompt_content = response.text
        word_count = len(prompt_content.split())

        # Store the prompt
        try:
            report_id = await db.fetchval(
                """
                INSERT INTO muse_reports (session_id, style_guide_id, report_type, report_content, format)
                VALUES ($1, $2, 'cursor_prompt', $3, 'markdown')
                RETURNING id
                """,
                session_id,
                style_guide["id"],
                prompt_content
            )
            logger.info(f"[MUSE Report] Cursor prompt {report_id} stored for session {session_id}")
        except Exception as e:
            logger.warning(f"[MUSE Report] Failed to store prompt: {e}")

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        return GeneratedReport(
            report_type="cursor_prompt",
            title=f"Implementation Prompt: {session['project_name']}",
            content_markdown=prompt_content,
            word_count=word_count,
            generation_model=response.model,
            generation_tokens=response.total_tokens,
            generation_duration_ms=duration_ms
        )

    async def generate_export_package(
        self,
        session_id: int,
        project_id: Optional[int] = None,
        format_type: str = "cursor_ready"
    ) -> ExportPackage:
        """
        Generates a ZIP package with all design documentation.
        
        Package contents vary by format_type:
        - full: Everything (report, prompt, style guide, tokens, moodboard images)
        - cursor_ready: Prompt + style guide + tokens
        - tokens_only: Just the design tokens and Tailwind config
        
        Args:
            session_id: The research session ID
            project_id: Optional project ID
            format_type: Package format (full, cursor_ready, tokens_only)
            
        Returns:
            ExportPackage with ZIP data and manifest
        """
        data = await self._get_session_data(session_id)
        session = data["session"]
        style_guide = data["style_guide"]

        if not style_guide:
            raise ValueError(f"No approved style guide found for session {session_id}.")

        project_name = session["project_name"].lower().replace(" ", "-")
        
        # Collect files to include
        files_to_include: Dict[str, str] = {}
        
        # Always include the cursor prompt
        cursor_prompt = await self._get_or_generate_prompt(session_id, "cursor_prompt", style_guide["id"])
        files_to_include["cursor-prompt.md"] = cursor_prompt
        
        # Always include style guide JSON
        style_guide_json = json.dumps(style_guide, indent=2, default=str)
        files_to_include["style-guide.json"] = style_guide_json
        
        # Generate Tailwind config from style guide
        tailwind_config = self._generate_tailwind_config(style_guide)
        files_to_include["tailwind.config.ts"] = tailwind_config
        
        # Generate CSS variables
        css_variables = self._generate_css_variables(style_guide)
        files_to_include["design-tokens.css"] = css_variables
        
        if format_type == "full":
            # Include design report
            design_report = await self._get_or_generate_prompt(session_id, "design_report", style_guide["id"])
            files_to_include["design-report.md"] = design_report
            
            # Include README
            readme = self._generate_readme(session, style_guide)
            files_to_include["README.md"] = readme
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, 'w', ZIP_DEFLATED) as zipf:
            for filename, content in files_to_include.items():
                if isinstance(content, str):
                    zipf.writestr(filename, content.encode('utf-8'))
                else:
                    zipf.writestr(filename, content)
        
        zip_data = zip_buffer.getvalue()
        
        return ExportPackage(
            package_name=f"{project_name}-design-package",
            package_format=format_type,
            size_bytes=len(zip_data),
            contents_manifest={"files": list(files_to_include.keys())},
            zip_data=zip_data
        )

    async def _get_or_generate_prompt(
        self,
        session_id: int,
        report_type: str,
        style_guide_id: int
    ) -> str:
        """Get existing report from DB or generate new one."""
        # Try to get existing
        existing = await db.fetchrow(
            "SELECT report_content FROM muse_reports WHERE session_id = $1 AND report_type = $2",
            session_id, report_type
        )
        
        if existing:
            return existing["report_content"]
        
        # Generate new
        if report_type == "cursor_prompt":
            result = await self.generate_cursor_prompt(session_id)
        else:
            result = await self.generate_design_report(session_id)
        
        return result.content_markdown

    def _generate_tailwind_config(self, style_guide: Dict[str, Any]) -> str:
        """Generate Tailwind config from style guide."""
        colors = json.loads(style_guide.get("colors", "{}")) if isinstance(style_guide.get("colors"), str) else style_guide.get("colors", {})
        typography = json.loads(style_guide.get("typography", "{}")) if isinstance(style_guide.get("typography"), str) else style_guide.get("typography", {})
        spacing = json.loads(style_guide.get("spacing", "{}")) if isinstance(style_guide.get("spacing"), str) else style_guide.get("spacing", {})
        
        config = f'''import type {{ Config }} from "tailwindcss";

const config: Config = {{
  content: [
    "./src/**/*.{{js,ts,jsx,tsx,mdx}}",
    "./app/**/*.{{js,ts,jsx,tsx,mdx}}",
    "./components/**/*.{{js,ts,jsx,tsx,mdx}}",
  ],
  theme: {{
    extend: {{
      colors: {json.dumps(colors, indent=8)},
      fontFamily: {{
        heading: ["{typography.get('heading_font', 'Inter')}", "sans-serif"],
        body: ["{typography.get('body_font', 'Inter')}", "sans-serif"],
      }},
      spacing: {json.dumps(spacing, indent=8) if spacing else "{}"},
    }},
  }},
  plugins: [],
}};

export default config;
'''
        return config

    def _generate_css_variables(self, style_guide: Dict[str, Any]) -> str:
        """Generate CSS custom properties from style guide."""
        colors = json.loads(style_guide.get("colors", "{}")) if isinstance(style_guide.get("colors"), str) else style_guide.get("colors", {})
        typography = json.loads(style_guide.get("typography", "{}")) if isinstance(style_guide.get("typography"), str) else style_guide.get("typography", {})
        spacing = json.loads(style_guide.get("spacing", "{}")) if isinstance(style_guide.get("spacing"), str) else style_guide.get("spacing", {})
        
        lines = [":root {"]
        
        # Colors
        lines.append("  /* Colors */")
        for name, value in colors.items():
            if isinstance(value, str):
                css_name = name.replace("_", "-")
                lines.append(f"  --color-{css_name}: {value};")
            elif isinstance(value, dict) and "hex" in value:
                css_name = name.replace("_", "-")
                lines.append(f"  --color-{css_name}: {value['hex']};")
        
        # Typography
        lines.append("")
        lines.append("  /* Typography */")
        if typography:
            lines.append(f"  --font-heading: '{typography.get('heading_font', 'Inter')}', sans-serif;")
            lines.append(f"  --font-body: '{typography.get('body_font', 'Inter')}', sans-serif;")
        
        # Spacing
        if spacing:
            lines.append("")
            lines.append("  /* Spacing */")
            for name, value in spacing.items():
                css_name = name.replace("_", "-")
                lines.append(f"  --spacing-{css_name}: {value};")
        
        lines.append("}")
        
        return "\n".join(lines)

    def _generate_readme(self, session: Dict[str, Any], style_guide: Dict[str, Any]) -> str:
        """Generate README for the export package."""
        return f"""# {session['project_name']} - Design Package

## Overview

This package contains the complete design specification generated by Muse Design Research Agent.

**Design Brief:** {session['design_brief']}

**Target Audience:** {session.get('target_audience', 'Not specified')}

## Contents

- `cursor-prompt.md` - Detailed implementation prompt for AI coding assistants
- `design-report.md` - Comprehensive design report (full package only)
- `style-guide.json` - Complete style guide data
- `tailwind.config.ts` - Ready-to-use Tailwind configuration
- `design-tokens.css` - CSS custom properties

## Quick Start

1. Copy `tailwind.config.ts` to your project root
2. Import `design-tokens.css` in your global styles
3. Use `cursor-prompt.md` as context for your AI coding assistant

## Generated By

Muse Design Research Agent
Session ID: {session.get('id', 'N/A')}
Generated: {datetime.now(timezone.utc).isoformat()}
"""


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

report_generator = MuseReportGenerator()
