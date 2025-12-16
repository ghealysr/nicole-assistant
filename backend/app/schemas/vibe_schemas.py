"""
Vibe Dashboard V3.0 - Pydantic Schemas

Request/response models for enhanced Vibe endpoints.

Author: AlphaWave Architecture
Version: 3.0.0
"""

from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ProjectType(str, Enum):
    """Type of website project"""
    PORTFOLIO = "portfolio"
    BUSINESS = "business"
    ECOMMERCE = "ecommerce"
    LANDING = "landing"
    BLOG = "blog"
    OTHER = "other"


class IterationType(str, Enum):
    """Type of iteration/feedback"""
    BUG_FIX = "bug_fix"
    DESIGN_CHANGE = "design_change"
    FEATURE_ADD = "feature_add"


class FeedbackCategory(str, Enum):
    """Category of feedback"""
    VISUAL = "visual"
    FUNCTIONAL = "functional"
    CONTENT = "content"
    PERFORMANCE = "performance"


class Priority(str, Enum):
    """Priority level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FileType(str, Enum):
    """Type of uploaded file"""
    IMAGE = "image"
    DOCUMENT = "document"
    LOGO = "logo"
    INSPIRATION = "inspiration"
    BRAND_ASSET = "brand_asset"
    OTHER = "other"


# ============================================================================
# INTAKE SCHEMAS
# ============================================================================

class IntakeFormSchema(BaseModel):
    """
    Structured intake form for project setup.
    Replaces free-form chat intake.
    """
    
    # ========== Business Information ==========
    business_name: str = Field(..., min_length=1, max_length=200)
    business_description: str = Field(..., min_length=10, max_length=2000)
    target_audience: str = Field(..., min_length=5, max_length=500)
    
    # ========== Project Scope ==========
    project_type: ProjectType
    page_count_estimate: int = Field(..., ge=1, le=100)
    key_features: List[str] = Field(default_factory=list, max_items=20)
    
    # ========== Design Preferences ==========
    style_keywords: List[str] = Field(
        default_factory=list,
        max_items=10,
        description="e.g., 'modern', 'minimal', 'bold', 'elegant'"
    )
    color_preferences: Optional[str] = Field(None, max_length=500)
    avoid_colors: Optional[str] = Field(None, max_length=500)
    inspiration_notes: Optional[str] = Field(None, max_length=2000)
    
    # ========== Technical Requirements ==========
    needs_forms: bool = False
    needs_blog: bool = False
    needs_ecommerce: bool = False
    needs_cms: bool = False
    needs_authentication: bool = False
    needs_api: bool = False
    
    # ========== Additional ==========
    deadline: Optional[str] = Field(None, description="Human-readable deadline")
    budget_range: Optional[str] = Field(None, description="e.g., '$5k-$10k'")
    additional_notes: Optional[str] = Field(None, max_length=2000)
    
    @validator('key_features')
    def validate_key_features(cls, v):
        """Ensure features are not empty strings"""
        return [f.strip() for f in v if f.strip()]
    
    @validator('style_keywords')
    def validate_style_keywords(cls, v):
        """Ensure keywords are not empty strings"""
        return [k.strip().lower() for k in v if k.strip()]
    
    class Config:
        schema_extra = {
            "example": {
                "business_name": "Acme Photography",
                "business_description": "Professional photography services specializing in weddings and portraits",
                "target_audience": "Engaged couples and families in the NYC area",
                "project_type": "portfolio",
                "page_count_estimate": 5,
                "key_features": ["Gallery", "About", "Contact Form", "Testimonials"],
                "style_keywords": ["modern", "minimal", "elegant"],
                "color_preferences": "Earth tones, warm neutrals",
                "needs_forms": True,
                "needs_blog": False
            }
        }


class FileUploadRequest(BaseModel):
    """Metadata for file upload"""
    file_type: FileType
    description: Optional[str] = Field(None, max_length=500)


class CompetitorURLRequest(BaseModel):
    """Add competitor URL for research"""
    url: HttpUrl
    notes: Optional[str] = Field(None, max_length=1000)


# ============================================================================
# APPROVAL SCHEMAS
# ============================================================================

class ArchitectureApprovalRequest(BaseModel):
    """Glen approves architecture"""
    approved_by: str = Field(..., description="User ID or name")


class ArchitectureRevisionRequest(BaseModel):
    """Glen requests architecture changes"""
    feedback: str = Field(..., min_length=10, max_length=2000)
    requested_by: str = Field(..., description="User ID or name")


# ============================================================================
# FEEDBACK/ITERATION SCHEMAS
# ============================================================================

class FeedbackSchema(BaseModel):
    """
    Glen's feedback on preview.
    Creates a new iteration.
    """
    
    feedback_type: IterationType
    description: str = Field(..., min_length=10, max_length=2000)
    category: Optional[FeedbackCategory] = None
    priority: Priority = Priority.MEDIUM
    affected_pages: Optional[List[str]] = Field(default_factory=list, max_items=20)
    screenshot_url: Optional[str] = None  # If Glen annotated a screenshot
    
    @validator('affected_pages')
    def validate_affected_pages(cls, v):
        """Ensure page names are not empty strings"""
        return [p.strip() for p in v if p.strip()]
    
    class Config:
        schema_extra = {
            "example": {
                "feedback_type": "bug_fix",
                "description": "The contact form submit button is not clickable on mobile",
                "category": "functional",
                "priority": "high",
                "affected_pages": ["/contact"]
            }
        }


class IterationResolveRequest(BaseModel):
    """Mark iteration as resolved"""
    changes_summary: str = Field(..., min_length=10, max_length=2000)
    files_affected: List[str] = Field(..., min_items=1, max_items=50)


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class UploadResponse(BaseModel):
    """File upload success response"""
    upload_id: int
    storage_url: str
    file_type: str
    original_filename: str
    file_size_bytes: int
    created_at: datetime


class CompetitorResponse(BaseModel):
    """Competitor URL response"""
    competitor_id: int
    url: str
    screenshot_url: Optional[str]
    notes: Optional[str]
    created_at: datetime


class QAScoresResponse(BaseModel):
    """QA scores for display"""
    
    score_id: int
    project_id: int
    
    # Lighthouse scores
    lighthouse_performance: Optional[int] = Field(None, ge=0, le=100)
    lighthouse_accessibility: Optional[int] = Field(None, ge=0, le=100)
    lighthouse_best_practices: Optional[int] = Field(None, ge=0, le=100)
    lighthouse_seo: Optional[int] = Field(None, ge=0, le=100)
    
    # Core Web Vitals
    lcp_score: Optional[float] = None
    fid_score: Optional[float] = None
    cls_score: Optional[float] = None
    
    # Accessibility
    accessibility_violations: int
    accessibility_warnings: int
    accessibility_passes: int
    
    # Tests
    tests_total: int
    tests_passed: int
    tests_failed: int
    test_coverage_percent: Optional[float] = None
    
    # Screenshots
    screenshot_mobile: Optional[str]
    screenshot_tablet: Optional[str]
    screenshot_desktop: Optional[str]
    
    # Computed status
    all_passing: bool
    
    # Timestamp
    created_at: datetime
    
    class Config:
        orm_mode = True


class IterationResponse(BaseModel):
    """Iteration for display"""
    
    iteration_id: int
    project_id: int
    iteration_number: int
    iteration_type: str
    feedback: str
    feedback_category: Optional[str]
    priority: str
    status: str
    affected_pages: Optional[List[str]]
    files_affected: Optional[List[str]]
    changes_summary: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    
    class Config:
        orm_mode = True


class ProjectChatContext(BaseModel):
    """Full project context for Nicole chat"""
    
    project_id: int
    project_name: str
    status: str
    
    # Intake data
    brief: Optional[Dict[str, Any]]
    intake_form: Optional[Dict[str, Any]]
    uploads: List[UploadResponse]
    competitors: List[CompetitorResponse]
    
    # Architecture
    architecture: Optional[Dict[str, Any]]
    architecture_approved: bool
    
    # Build
    files_count: int
    chunks_completed: int
    total_chunks: int
    
    # QA
    latest_qa_scores: Optional[QAScoresResponse]
    
    # Iterations
    iterations: List[IterationResponse]
    iteration_count: int
    max_iterations: int
    
    # URLs
    preview_url: Optional[str]
    deployment_url: Optional[str]
    github_repo_url: Optional[str]
    
    # Recent activity
    recent_activities: List[Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "description": "Complete project context for Nicole to understand project state"
        }


# ============================================================================
# BULK RESPONSE SCHEMAS
# ============================================================================

class IterationListResponse(BaseModel):
    """List of iterations"""
    iterations: List[IterationResponse]
    total: int
    current_iteration: int
    max_iterations: int


class QAScoresListResponse(BaseModel):
    """List of QA scores (history)"""
    scores: List[QAScoresResponse]
    total: int
    latest: Optional[QAScoresResponse]
