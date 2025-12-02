"""
Nicole V7 - Tool Use Examples Service

Implements Anthropic's Tool Use Examples pattern for improved parameter accuracy.

Problem: Tool schemas alone don't always convey how to use a tool correctly.
Claude might pass parameters in wrong formats or miss required combinations.

Solution: Provide concrete examples alongside tool schemas showing:
- Input/output pairs
- Edge cases
- Common patterns
- Error cases to avoid

Impact: 72% → 90% accuracy improvement on tool parameter selection (Anthropic benchmark)

Author: Nicole V7 Architecture
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ToolExample:
    """A concrete example of tool usage."""
    description: str  # What this example demonstrates
    input_params: Dict[str, Any]  # Example input parameters
    expected_output: Optional[str] = None  # What to expect
    notes: Optional[str] = None  # Additional guidance
    is_negative: bool = False  # If True, this is a "don't do this" example


@dataclass
class ToolExamplesCollection:
    """Collection of examples for a tool."""
    tool_name: str
    examples: List[ToolExample] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)


class ToolExamplesService:
    """
    Service for managing tool usage examples.
    
    Provides concrete examples that get injected into tool definitions
    to improve Claude's accuracy when using tools.
    """
    
    def __init__(self):
        self._examples: Dict[str, ToolExamplesCollection] = {}
        self._initialize_core_examples()
        logger.info(f"[TOOL EXAMPLES] Service initialized with {len(self._examples)} tools")
    
    def _initialize_core_examples(self):
        """Initialize examples for core Nicole tools."""
        
        # Memory Search examples
        self.add_examples(
            tool_name="memory_search",
            examples=[
                ToolExample(
                    description="Search for user preferences",
                    input_params={
                        "query": "favorite color",
                        "limit": 5,
                        "min_confidence": 0.5
                    },
                    expected_output="List of memories about the user's color preferences",
                    notes="Use specific keywords from the user's question"
                ),
                ToolExample(
                    description="Search for factual information",
                    input_params={
                        "query": "birthday date",
                        "memory_type": "fact",
                        "limit": 3
                    },
                    expected_output="Specific date facts from memory",
                    notes="Filter by memory_type for more precise results"
                ),
                ToolExample(
                    description="Search conversation history",
                    input_params={
                        "query": "project discussion",
                        "memory_type": "conversation",
                        "limit": 10
                    },
                    expected_output="Past conversation snippets about projects"
                ),
            ],
            common_mistakes=[
                "Don't use overly broad queries like 'everything about user'",
                "Don't set limit too high - 5-10 is usually sufficient",
                "Don't ignore min_confidence - low confidence memories may be outdated"
            ],
            best_practices=[
                "Extract key nouns from user question for query",
                "Use memory_type filter when you know what you're looking for",
                "Search before responding to personalization questions"
            ]
        )
        
        # Memory Store examples
        self.add_examples(
            tool_name="memory_store",
            examples=[
                ToolExample(
                    description="Store a user preference",
                    input_params={
                        "content": "User prefers dark mode in applications",
                        "memory_type": "preference",
                        "tags": ["ui", "preference", "dark-mode"],
                        "importance": "medium"
                    },
                    expected_output="Memory stored successfully",
                    notes="Use clear, factual language for stored content"
                ),
                ToolExample(
                    description="Store a family fact",
                    input_params={
                        "content": "Austin (eldest son) is interested in technology and gaming",
                        "memory_type": "fact",
                        "tags": ["family", "austin", "interests"],
                        "importance": "high"
                    },
                    expected_output="Family information stored"
                ),
                ToolExample(
                    description="BAD: Storing vague information",
                    input_params={
                        "content": "User mentioned something about work",
                        "memory_type": "general"
                    },
                    is_negative=True,
                    notes="Too vague - store specific, actionable information"
                ),
            ],
            common_mistakes=[
                "Don't store conversation filler ('um', 'you know')",
                "Don't store information that contradicts existing high-confidence memories without verification",
                "Don't store sensitive information without appropriate tags"
            ],
            best_practices=[
                "Store specific, factual information",
                "Use appropriate memory_type (preference, fact, task, relationship)",
                "Add relevant tags for better searchability",
                "Mark family/personal info as high importance"
            ]
        )
        
        # Document Search examples
        self.add_examples(
            tool_name="document_search",
            examples=[
                ToolExample(
                    description="Search for specific information in documents",
                    input_params={
                        "query": "contract termination clause",
                        "limit": 3
                    },
                    expected_output="Relevant document chunks with page numbers",
                    notes="Use specific terms that would appear in the document"
                ),
                ToolExample(
                    description="Search across all documents",
                    input_params={
                        "query": "quarterly revenue projections",
                        "limit": 5
                    },
                    expected_output="Matching content from financial documents"
                ),
            ],
            common_mistakes=[
                "Don't search for concepts not in the documents",
                "Don't use overly broad queries that return irrelevant results"
            ],
            best_practices=[
                "Use domain-specific terminology from the user's field",
                "Combine with memory search to understand document context"
            ]
        )
        
        # Think tool examples
        self.add_examples(
            tool_name="think",
            examples=[
                ToolExample(
                    description="Planning a multi-step operation",
                    input_params={
                        "thought": """The user wants me to send a report to their team.
Let me break this down:
1. Which report? User mentioned 'the quarterly report' - I should search documents
2. Who is the team? I should search memory for team member information
3. How to send? Email seems appropriate based on past patterns

Plan:
1. Search documents for 'quarterly report'
2. Search memory for 'team members' or 'team email'
3. Compose email with report content
4. Confirm with user before sending""",
                        "category": "multi_step_planning",
                        "conclusion": "Search for report first, then team members"
                    }
                ),
                ToolExample(
                    description="Handling ambiguous request",
                    input_params={
                        "thought": """The user said 'remind me about that thing tomorrow.'
This is ambiguous:
- 'that thing' - what thing? No recent context about a specific task
- 'tomorrow' - what time tomorrow?

I have two options:
1. Ask for clarification now
2. Check memory for recent tasks and infer

Given no recent context about tasks, I should ask for clarification.
I'll ask: 'What would you like me to remind you about, and what time tomorrow?'""",
                        "category": "clarification",
                        "conclusion": "Ask user for specific details"
                    }
                ),
                ToolExample(
                    description="Safety/policy consideration",
                    input_params={
                        "thought": """The user asked for investment advice on a specific stock.
According to my guidelines:
- I can provide general financial education
- I should NOT give specific buy/sell recommendations
- I should recommend consulting a financial advisor

I'll share general information about how to evaluate stocks,
but clearly state this isn't financial advice.""",
                        "category": "safety_check",
                        "conclusion": "Provide educational info, recommend professional advice"
                    }
                ),
            ],
            common_mistakes=[
                "Don't think about trivial decisions (saves tokens)",
                "Don't use think tool for simple factual responses",
                "Don't over-analyze when the request is clear"
            ],
            best_practices=[
                "Use think tool before multi-step tool chains",
                "Use for ambiguous requests to decide on clarification",
                "Use for policy/safety decisions",
                "Keep thoughts structured and conclusion-oriented"
            ]
        )
        
        # Gmail examples (for when Gmail MCP is connected)
        self.add_examples(
            tool_name="gmail_send",
            examples=[
                ToolExample(
                    description="Send a simple email",
                    input_params={
                        "to": "team@company.com",
                        "subject": "Weekly Update - Dec 2",
                        "body": "Hi team,\n\nHere's our weekly update...\n\nBest,\nGlen"
                    },
                    expected_output="Email sent successfully"
                ),
                ToolExample(
                    description="Send with CC and attachments",
                    input_params={
                        "to": "client@example.com",
                        "cc": ["manager@company.com"],
                        "subject": "Project Proposal",
                        "body": "Please find attached...",
                        "attachments": ["proposal.pdf"]
                    }
                ),
            ],
            common_mistakes=[
                "Don't send without confirming recipient with user",
                "Don't use informal language for business emails",
                "Don't forget to include greeting and signature"
            ],
            best_practices=[
                "Confirm recipient and subject with user before sending",
                "Use appropriate tone based on recipient relationship",
                "Include clear call-to-action when appropriate"
            ]
        )
        
        # Calendar examples
        self.add_examples(
            tool_name="calendar_create_event",
            examples=[
                ToolExample(
                    description="Create a meeting",
                    input_params={
                        "title": "Team Standup",
                        "start_time": "2025-12-03T09:00:00",
                        "end_time": "2025-12-03T09:30:00",
                        "attendees": ["team@company.com"],
                        "description": "Daily standup meeting"
                    }
                ),
                ToolExample(
                    description="Create an all-day event",
                    input_params={
                        "title": "Project Deadline",
                        "all_day": True,
                        "date": "2025-12-15",
                        "description": "Final delivery for Q4 project"
                    }
                ),
            ],
            common_mistakes=[
                "Don't create events without confirming time with user",
                "Don't use relative times ('tomorrow') - convert to ISO format",
                "Don't forget timezone considerations"
            ],
            best_practices=[
                "Always confirm date/time with user before creating",
                "Use ISO 8601 format for times",
                "Include relevant attendees for meetings"
            ]
        )
    
    def add_examples(
        self,
        tool_name: str,
        examples: List[ToolExample],
        common_mistakes: Optional[List[str]] = None,
        best_practices: Optional[List[str]] = None
    ) -> ToolExamplesCollection:
        """
        Add examples for a tool.
        
        Args:
            tool_name: Name of the tool
            examples: List of example usages
            common_mistakes: Things to avoid
            best_practices: Recommended patterns
            
        Returns:
            The examples collection
        """
        collection = ToolExamplesCollection(
            tool_name=tool_name,
            examples=examples,
            common_mistakes=common_mistakes or [],
            best_practices=best_practices or []
        )
        
        self._examples[tool_name] = collection
        logger.debug(f"[TOOL EXAMPLES] Added {len(examples)} examples for {tool_name}")
        return collection
    
    def get_examples(self, tool_name: str) -> Optional[ToolExamplesCollection]:
        """Get examples for a tool."""
        return self._examples.get(tool_name)
    
    def format_for_tool_description(self, tool_name: str) -> str:
        """
        Format examples as a string to append to tool description.
        
        This creates an enhanced description with examples that
        significantly improves Claude's parameter accuracy.
        """
        collection = self._examples.get(tool_name)
        if not collection:
            return ""
        
        parts = []
        
        # Add positive examples
        positive_examples = [e for e in collection.examples if not e.is_negative]
        if positive_examples:
            parts.append("\n\n**Examples:**")
            for i, ex in enumerate(positive_examples[:3], 1):  # Limit to 3
                parts.append(f"\n{i}. {ex.description}")
                parts.append(f"   Input: {ex.input_params}")
                if ex.notes:
                    parts.append(f"   Note: {ex.notes}")
        
        # Add common mistakes (briefly)
        if collection.common_mistakes:
            parts.append("\n\n**Avoid:**")
            for mistake in collection.common_mistakes[:2]:  # Limit to 2
                parts.append(f"\n- {mistake}")
        
        return "".join(parts)
    
    def enhance_tool_schema(self, tool_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a tool schema with examples.
        
        Appends formatted examples to the tool's description.
        """
        tool_name = tool_schema.get("name", "")
        examples_text = self.format_for_tool_description(tool_name)
        
        if examples_text:
            enhanced = tool_schema.copy()
            enhanced["description"] = tool_schema.get("description", "") + examples_text
            return enhanced
        
        return tool_schema
    
    def get_prompt_injection(self) -> str:
        """
        Get system prompt guidance about tool usage patterns.
        """
        return """
## 🎯 TOOL USAGE BEST PRACTICES

When using tools, follow these patterns for best results:

**Before using a tool:**
1. Think about what parameters you need
2. Check if you have all required information
3. If unsure, ask the user for clarification

**Memory tools:**
- Search before storing to avoid duplicates
- Use specific queries with relevant keywords
- Filter by memory_type when you know what you're looking for
- Store factual, specific information (not vague notes)

**Communication tools:**
- ALWAYS confirm recipients before sending
- Match tone to the relationship (formal/casual)
- Include appropriate greetings and signatures

**Calendar tools:**
- Convert relative times ("tomorrow 3pm") to ISO format
- Confirm date/time with user before creating
- Include relevant attendees

**Think tool:**
- Use for multi-step planning
- Use for ambiguous requests
- Use for policy/safety decisions
- Keep thoughts structured with clear conclusions
"""


# Global service instance
tool_examples_service = ToolExamplesService()

