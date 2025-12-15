"""
Multi-Model Orchestrator for AlphaWave Vibe

NYC Design Agency Quality Agent Team led by Nicole.

AGENT PIPELINE:
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NICOLE (Creative Director)                        │
│                    The authority - orchestrates all agents                  │
├─────────────────┬─────────────────┬──────────────────┬──────────────────────┤
│  DESIGN AGENT   │ ARCHITECT AGENT │  CODING AGENT    │    QA AGENT          │
│  🎨             │ 🏗️              │  💻              │    🔍                │
├─────────────────┼─────────────────┼──────────────────┼──────────────────────┤
│ Visual Research │ System Design   │ Implementation   │ Quality Assurance    │
│ Color Theory    │ Component Arch  │ Code Generation  │ Accessibility        │
│ Typography      │ Data Flow       │ Styling          │ Performance          │
│ Trend Analysis  │ SEO Strategy    │ Interactions     │ Security             │
└─────────────────┴─────────────────┴──────────────────┴──────────────────────┘

STANDARDS:
- Code as if Elon Musk and Sam Altman will review it
- NYC design agency quality - Webby Award worthy
- Cutting-edge, futuristic, flawless execution
- Each agent owns their phase completely

Author: AlphaWave Architecture
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """What each model excels at."""
    DESIGN_RESEARCH = "design_research"      # Visual trends, colors, inspiration
    WEB_GROUNDING = "web_grounding"          # Real-time web search
    ARCHITECTURE = "architecture"            # System design, planning
    CODE_GENERATION = "code_generation"      # Writing code
    CODE_REVIEW = "code_review"              # QA, finding issues
    JUDGMENT = "judgment"                    # Final approval decisions
    CONVERSATION = "conversation"            # Chat, intake


@dataclass
class ModelHealth:
    """Tracks health status of a model."""
    name: str
    available: bool = True
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    cooldown_until: Optional[datetime] = None
    
    def record_success(self):
        """Record successful call."""
        self.available = True
        self.consecutive_failures = 0
        self.cooldown_until = None
    
    def record_failure(self, error: str):
        """Record failed call and potentially enter cooldown."""
        self.last_failure = datetime.utcnow()
        self.consecutive_failures += 1
        
        # Enter cooldown after 3 consecutive failures
        if self.consecutive_failures >= 3:
            # Exponential cooldown: 30s, 60s, 120s, max 5min
            cooldown_seconds = min(30 * (2 ** (self.consecutive_failures - 3)), 300)
            self.cooldown_until = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
            self.available = False
            logger.warning(
                f"[ORCHESTRATOR] {self.name} entering cooldown for {cooldown_seconds}s "
                f"after {self.consecutive_failures} failures"
            )
    
    def check_available(self) -> bool:
        """Check if model is available (not in cooldown)."""
        if self.cooldown_until and datetime.utcnow() < self.cooldown_until:
            return False
        
        # Cooldown expired, reset
        if self.cooldown_until and datetime.utcnow() >= self.cooldown_until:
            self.cooldown_until = None
            self.available = True
            self.consecutive_failures = 0
            logger.info(f"[ORCHESTRATOR] {self.name} cooldown expired, now available")
        
        return self.available


@dataclass
class DesignSystem:
    """Generated design system from Gemini."""
    colors: Dict[str, str] = field(default_factory=dict)
    typography: Dict[str, str] = field(default_factory=dict)
    spacing: Dict[str, str] = field(default_factory=dict)
    inspiration_notes: str = ""
    trends_applied: List[str] = field(default_factory=list)
    generated_by: str = "gemini"


@dataclass
class AgentTask:
    """A task assigned by Nicole to an agent."""
    task_id: str
    agent: str  # "gemini-3-pro", "claude-opus", "claude-sonnet"
    task_type: str  # "design", "architecture", "build", "qa", "review"
    description: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class NicoleAgentAuthority:
    """
    Nicole's authority over the agent team.
    
    Nicole orchestrates all agents and maintains oversight:
    - Assigns tasks to appropriate agents
    - Reviews agent output for quality
    - Intervenes when agents produce subpar results
    - Tracks agent performance and adjusts accordingly
    """
    
    def __init__(self):
        self.active_tasks: Dict[str, AgentTask] = {}
        self.task_history: List[AgentTask] = []
        self._task_counter = 0
    
    def assign_task(
        self,
        agent: str,
        task_type: str,
        description: str,
        project_id: int
    ) -> AgentTask:
        """Nicole assigns a task to an agent."""
        self._task_counter += 1
        task_id = f"task_{project_id}_{self._task_counter}"
        
        task = AgentTask(
            task_id=task_id,
            agent=agent,
            task_type=task_type,
            description=description,
            status="running"
        )
        
        self.active_tasks[task_id] = task
        logger.info(f"[NICOLE] Assigned {task_type} to {agent}: {description[:50]}...")
        
        return task
    
    def complete_task(
        self,
        task_id: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Mark a task as completed."""
        task = self.active_tasks.pop(task_id, None)
        if task:
            task.completed_at = datetime.utcnow()
            task.status = "completed" if success else "failed"
            task.result = result
            task.error = error
            self.task_history.append(task)
            
            duration = (task.completed_at - task.started_at).total_seconds()
            logger.info(
                f"[NICOLE] Task {task_id} {'completed' if success else 'failed'} "
                f"by {task.agent} in {duration:.1f}s"
            )
    
    def get_agent_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for each agent."""
        metrics: Dict[str, Dict[str, Any]] = {}
        
        for task in self.task_history:
            if task.agent not in metrics:
                metrics[task.agent] = {
                    "total_tasks": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_duration": 0.0,
                    "durations": []
                }
            
            m = metrics[task.agent]
            m["total_tasks"] += 1
            if task.status == "completed":
                m["successful"] += 1
            else:
                m["failed"] += 1
            
            if task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds()
                m["durations"].append(duration)
        
        # Calculate averages
        for agent, m in metrics.items():
            if m["durations"]:
                m["avg_duration"] = sum(m["durations"]) / len(m["durations"])
            del m["durations"]  # Don't expose raw list
        
        return metrics
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get currently active tasks for all agents."""
        return [
            {
                "task_id": t.task_id,
                "agent": t.agent,
                "task_type": t.task_type,
                "description": t.description,
                "running_for": (datetime.utcnow() - t.started_at).total_seconds()
            }
            for t in self.active_tasks.values()
        ]


# Global Nicole authority instance
nicole_authority = NicoleAgentAuthority()


class ModelOrchestrator:
    """
    Orchestrates multi-model AI workflow for Vibe Dashboard.
    
    Design Philosophy (Anthropic-style):
    1. Use the right model for each task based on capabilities
    2. Implement graceful degradation with fallbacks
    3. Track model health and adapt routing
    4. Provide clear observability into model decisions
    """
    
    # Agent-to-Model mapping (role-based naming)
    AGENT_MODELS = {
        "design_agent": "gemini-3-pro",      # Web research, visual creativity
        "architect_agent": "claude-opus",     # Complex reasoning
        "coding_agent": "claude-sonnet",      # Fast, accurate code
        "qa_agent": "claude-sonnet",          # Systematic review
        "review_agent": "claude-opus",        # Judgment calls
    }
    
    # Model capability mapping - which agents handle which capabilities
    MODEL_CAPABILITIES = {
        "design_agent": [
            ModelCapability.DESIGN_RESEARCH,
            ModelCapability.WEB_GROUNDING,
        ],
        "architect_agent": [
            ModelCapability.ARCHITECTURE,
            ModelCapability.JUDGMENT,
        ],
        "coding_agent": [
            ModelCapability.CODE_GENERATION,
            ModelCapability.CONVERSATION,
        ],
        "qa_agent": [
            ModelCapability.CODE_REVIEW,
        ],
    }
    
    # Fallback chains for each capability (by agent role)
    FALLBACK_CHAINS = {
        ModelCapability.DESIGN_RESEARCH: ["design_agent", "architect_agent"],
        ModelCapability.WEB_GROUNDING: ["design_agent", "coding_agent"],
        ModelCapability.ARCHITECTURE: ["architect_agent", "coding_agent"],
        ModelCapability.CODE_GENERATION: ["coding_agent", "design_agent"],
        ModelCapability.CODE_REVIEW: ["qa_agent", "architect_agent"],
        ModelCapability.JUDGMENT: ["architect_agent", "coding_agent"],
        ModelCapability.CONVERSATION: ["coding_agent", "architect_agent"],
    }
    
    def __init__(self):
        """Initialize orchestrator with agent health tracking."""
        self.model_health: Dict[str, ModelHealth] = {
            "design_agent": ModelHealth("design_agent"),
            "architect_agent": ModelHealth("architect_agent"),
            "coding_agent": ModelHealth("coding_agent"),
            "qa_agent": ModelHealth("qa_agent"),
            "review_agent": ModelHealth("review_agent"),
        }
        
        # Lazy imports to avoid circular dependencies
        self._gemini_client = None
        self._claude_client = None
    
    @property
    def gemini(self):
        """Lazy-load Gemini client."""
        if self._gemini_client is None:
            from app.integrations.alphawave_gemini import gemini_client
            self._gemini_client = gemini_client
        return self._gemini_client
    
    @property
    def claude(self):
        """Lazy-load Claude client."""
        if self._claude_client is None:
            from app.integrations.alphawave_claude import claude_client
            self._claude_client = claude_client
        return self._claude_client
    
    def get_best_model(self, capability: ModelCapability) -> Optional[str]:
        """
        Get the best available model for a capability.
        
        Returns the first healthy model in the fallback chain.
        """
        chain = self.FALLBACK_CHAINS.get(capability, [])
        
        for model in chain:
            health = self.model_health.get(model)
            if health and health.check_available():
                return model
        
        # All models in chain are unavailable
        logger.error(f"[ORCHESTRATOR] No available models for {capability.value}")
        return None
    
    def record_result(self, model: str, success: bool, error: Optional[str] = None):
        """Record the result of a model call."""
        health = self.model_health.get(model)
        if health:
            if success:
                health.record_success()
            else:
                health.record_failure(error or "Unknown error")
    
    async def generate_design_system(
        self,
        brief: Dict[str, Any],
        project_id: int
    ) -> DesignSystem:
        """
        Generate a design system using Gemini 3 Pro's creative and research capabilities.
        
        Nicole assigns this task to Gemini 3 Pro because it excels at:
        - Understanding visual trends via web grounding (real-time search)
        - Creative color palette generation based on industry research
        - Typography recommendations based on current trends
        - Modern design pattern suggestions with real examples
        """
        model = self.get_best_model(ModelCapability.DESIGN_RESEARCH)
        
        # Nicole assigns the design task
        task = nicole_authority.assign_task(
            agent=model or "gemini-3-pro",
            task_type="design",
            description=f"Research and generate design system for {brief.get('business_name', 'project')}",
            project_id=project_id
        )
        
        try:
            if model == "design_agent" and self.gemini.is_configured:
                try:
                    result = await self._generate_design_with_gemini(brief, project_id)
                    nicole_authority.complete_task(task.task_id, True, {"generated_by": "design_agent"})
                    return result
                except Exception as e:
                    logger.warning(f"[ORCHESTRATOR] Design Agent failed: {e}")
                    self.record_result("design_agent", False, str(e))
                    # Fall through to Architect Agent as fallback
            
            # Fallback to Architect Agent for design (uses Claude Opus)
            logger.info("[ORCHESTRATOR] Nicole reassigning design task to Architect Agent")
            result = await self._generate_design_with_claude(brief, project_id)
            nicole_authority.complete_task(task.task_id, True, {"generated_by": "architect_agent"})
            return result
            
        except Exception as e:
            nicole_authority.complete_task(task.task_id, False, error=str(e))
            raise
    
    async def _generate_design_with_gemini(
        self,
        brief: Dict[str, Any],
        project_id: int
    ) -> DesignSystem:
        """Use Gemini to research and generate a design system."""
        business_type = brief.get("business_type", brief.get("project_type", "business"))
        business_name = brief.get("business_name", "Client")
        description = brief.get("description", "")
        
        # Step 1: Research current design trends for this industry
        research_query = f"""
        Current web design trends for {business_type} websites in 2025.
        Looking for:
        - Modern color palettes that work for {business_type}
        - Typography combinations that convey {brief.get('brand_feel', 'professional')}
        - Layout patterns that are popular for {business_type} sites
        - Specific examples from successful {business_type} websites
        """
        
        research_result = await self.gemini.deep_research(
            query=research_query,
            research_type="inspiration"
        )
        
        # Step 2: Generate design system based on research
        design_prompt = f"""
        Based on current design trends and this client brief, create a design system:

        Business: {business_name}
        Type: {business_type}
        Description: {description}
        Brand Feel: {brief.get('brand_feel', 'professional, trustworthy')}

        Research findings: {research_result.get('summary', '')}

        Generate a cohesive design system as JSON with:
        {{
            "colors": {{
                "primary": "#hexcode - main brand color",
                "secondary": "#hexcode - supporting color", 
                "accent": "#hexcode - call-to-action color",
                "text": "#hexcode",
                "text_light": "#hexcode",
                "background": "#hexcode"
            }},
            "typography": {{
                "heading_font": "Font name from Google Fonts",
                "body_font": "Font name from Google Fonts",
                "heading_weight": "600 or 700",
                "body_weight": "400"
            }},
            "spacing": {{
                "section_padding": "tailwind classes like py-16 md:py-24",
                "container": "max-w-7xl mx-auto px-4"
            }},
            "style_notes": "Brief description of the visual style",
            "trends_applied": ["trend1", "trend2"]
        }}
        """
        
        design_response = await self.gemini.deep_research(
            query=design_prompt,
            research_type="general"
        )
        
        self.record_result("design_agent", True)
        
        # Parse the response
        design_data = design_response.get("structured_data", {})
        if not design_data:
            # Try to extract from summary
            import json
            import re
            summary = design_response.get("summary", "")
            json_match = re.search(r'\{[^{}]*"colors"[^{}]*\}', summary, re.DOTALL)
            if json_match:
                try:
                    design_data = json.loads(json_match.group())
                except:
                    pass
        
        return DesignSystem(
            colors=design_data.get("colors", {
                "primary": "#8B9D83",
                "secondary": "#F4E4BC",
                "accent": "#D4A574",
                "text": "#333333",
                "text_light": "#666666",
                "background": "#FFFFFF"
            }),
            typography=design_data.get("typography", {
                "heading_font": "Playfair Display",
                "body_font": "Source Sans Pro",
                "heading_weight": "700",
                "body_weight": "400"
            }),
            spacing=design_data.get("spacing", {
                "section_padding": "py-16 md:py-24",
                "container": "max-w-7xl mx-auto px-4"
            }),
            inspiration_notes=design_data.get("style_notes", ""),
            trends_applied=design_data.get("trends_applied", []),
            generated_by="gemini"
        )
    
    async def _generate_design_with_claude(
        self,
        brief: Dict[str, Any],
        project_id: int
    ) -> DesignSystem:
        """Fallback: Use Claude to generate design system."""
        business_type = brief.get("business_type", brief.get("project_type", "business"))
        business_name = brief.get("business_name", "Client")
        
        prompt = f"""
        Create a design system for this website:
        
        Business: {business_name}
        Type: {business_type}
        Description: {brief.get('description', '')}
        Brand Feel: {brief.get('brand_feel', 'professional')}
        
        Output as JSON with colors, typography, and spacing.
        """
        
        try:
            response = await self.claude.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a professional web designer. Generate modern, attractive design systems.",
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.7
            )
            
            self.record_result("coding_agent", True)
            
            # Parse response (simplified)
            import json
            import re
            json_match = re.search(r'\{[^{}]*"colors"[^{}]*\}', response, re.DOTALL)
            if json_match:
                try:
                    design_data = json.loads(json_match.group())
                    return DesignSystem(
                        colors=design_data.get("colors", {}),
                        typography=design_data.get("typography", {}),
                        spacing=design_data.get("spacing", {}),
                        generated_by="claude"
                    )
                except:
                    pass
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Claude design fallback failed: {e}")
            self.record_result("coding_agent", False, str(e))
        
        # Return safe defaults
        return DesignSystem(
            colors={
                "primary": "#8B9D83",
                "secondary": "#F4E4BC", 
                "accent": "#D4A574"
            },
            typography={
                "heading_font": "Playfair Display",
                "body_font": "Source Sans Pro"
            },
            generated_by="default"
        )
    
    async def generate_with_fallback(
        self,
        capability: ModelCapability,
        prompt: str,
        system_prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.5
    ) -> Tuple[str, str]:
        """
        Generate content with automatic fallback.
        
        Returns: (response, model_used)
        """
        chain = self.FALLBACK_CHAINS.get(capability, ["claude-sonnet"])
        
        for model in chain:
            health = self.model_health.get(model)
            if not health or not health.check_available():
                continue
            
            try:
                if "gemini" in model:
                    response = await self.gemini.deep_research(
                        query=prompt,
                        research_type="general"
                    )
                    self.record_result(model, True)
                    return response.get("summary", ""), model
                
                elif "claude" in model:
                    claude_model = (
                        "claude-3-5-sonnet-20241022" if "sonnet" in model 
                        else "claude-3-opus-20240229"
                    )
                    response = await self.claude.generate_response(
                        messages=[{"role": "user", "content": prompt}],
                        system_prompt=system_prompt,
                        model=claude_model,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    self.record_result(model, True)
                    return response, model
                    
            except Exception as e:
                logger.warning(f"[ORCHESTRATOR] {model} failed: {e}")
                self.record_result(model, False, str(e))
                continue
        
        raise Exception("All models failed. Please try again later.")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health status summary for all models."""
        return {
            model: {
                "available": health.check_available(),
                "consecutive_failures": health.consecutive_failures,
                "cooldown_remaining": (
                    (health.cooldown_until - datetime.utcnow()).total_seconds()
                    if health.cooldown_until and health.cooldown_until > datetime.utcnow()
                    else 0
                )
            }
            for model, health in self.model_health.items()
        }


# Global orchestrator instance
model_orchestrator = ModelOrchestrator()

