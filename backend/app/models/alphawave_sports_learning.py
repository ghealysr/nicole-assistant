"""
Sports learning models for Nicole V7 Sports Oracle.
Tracks model performance improvements and user feedback.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class FeedbackType(str, Enum):
    """Types of feedback for sports predictions."""
    ACCURACY = "accuracy"
    REASONING = "reasoning"
    CONFIDENCE = "confidence"
    MODEL_CHOICE = "model_choice"
    TIMING = "timing"
    DATA_QUALITY = "data_quality"


class ModelAdjustmentType(str, Enum):
    """Types of model adjustments based on feedback."""
    WEIGHT_UPDATE = "weight_update"
    THRESHOLD_CHANGE = "threshold_change"
    FEATURE_ADDITION = "feature_addition"
    FEATURE_REMOVAL = "feature_removal"
    ALGORITHM_CHANGE = "algorithm_change"
    DATA_SOURCE_CHANGE = "data_source_change"


class LearningOutcome(str, Enum):
    """Outcomes of learning adjustments."""
    IMPROVED = "improved"
    DEGRADED = "degraded"
    NO_CHANGE = "no_change"
    NEEDS_MORE_DATA = "needs_more_data"


class AlphawaveSportsLearningLog(BaseModel):
    """
    Sports learning log for tracking model improvements.

    Records user feedback on predictions and tracks how the model
    adjusts based on learning from outcomes.

    Attributes:
        id: Unique learning entry identifier
        prediction_id: Related sports prediction
        user_id: User who provided feedback
        feedback_type: Type of feedback (accuracy, reasoning, etc.)
        feedback_value: Numerical score (0-1)
        user_comment: Optional detailed user comment
        model_adjustment: AI adjustments made based on feedback
        applied: Whether the adjustment was applied to the model
        outcome: Result of applying the adjustment
        created_at: When feedback was provided
    """

    id: UUID
    prediction_id: UUID
    user_id: UUID
    feedback_type: FeedbackType
    feedback_value: float = Field(..., ge=0.0, le=1.0, description="Feedback score 0-1")
    user_comment: Optional[str] = Field(None, description="Detailed user feedback")
    model_adjustment: Optional[Dict[str, Any]] = Field(None, description="Model changes applied")
    applied: bool = Field(default=False, description="Whether adjustment was applied")
    outcome: Optional[LearningOutcome] = None
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AlphawaveSportsLearningLogCreate(BaseModel):
    """Model for creating sports learning entries."""

    prediction_id: UUID
    feedback_type: FeedbackType
    feedback_value: float = Field(..., ge=0.0, le=1.0)
    user_comment: Optional[str] = None

    @validator('feedback_value')
    def validate_feedback_value(cls, v):
        """Ensure feedback value is reasonable."""
        if v < 0.0 or v > 1.0:
            raise ValueError("Feedback value must be between 0 and 1")
        return v


class AlphawaveModelPerformance(BaseModel):
    """
    Model performance tracking for sports predictions.

    Attributes:
        model_name: AI model used (claude-sonnet, claude-haiku, etc.)
        sport: Sport being predicted
        prediction_type: Type of prediction
        total_predictions: Total predictions made
        correct_predictions: Number correct
        accuracy_rate: Accuracy percentage
        average_confidence: Average confidence score
        average_error: Average prediction error
        improvement_rate: Rate of accuracy improvement over time
        last_updated: When metrics were last calculated
    """

    model_name: str
    sport: str
    prediction_type: str
    total_predictions: int
    correct_predictions: int
    accuracy_rate: float
    average_confidence: float
    average_error: Optional[float] = None
    improvement_rate: float
    last_updated: datetime

    class Config:
        from_attributes = True


class AlphawaveModelAdjustment(BaseModel):
    """
    Model adjustment tracking for learning improvements.

    Attributes:
        id: Unique adjustment identifier
        model_name: Model being adjusted
        sport: Sport affected
        adjustment_type: Type of adjustment made
        parameters_before: Model parameters before adjustment
        parameters_after: Model parameters after adjustment
        reasoning: Why adjustment was made
        expected_improvement: Expected accuracy improvement
        actual_improvement: Measured improvement
        applied_by: Who applied the adjustment (user or system)
        created_at: When adjustment was made
    """

    id: UUID
    model_name: str
    sport: str
    adjustment_type: ModelAdjustmentType
    parameters_before: Dict[str, Any]
    parameters_after: Dict[str, Any]
    reasoning: str
    expected_improvement: float
    actual_improvement: Optional[float] = None
    applied_by: str  # user_id or "system"
    created_at: datetime

    class Config:
        from_attributes = True


class AlphawaveModelAdjustmentCreate(BaseModel):
    """Model for creating model adjustments."""

    model_name: str
    sport: str
    adjustment_type: ModelAdjustmentType
    parameters_before: Dict[str, Any]
    parameters_after: Dict[str, Any]
    reasoning: str
    expected_improvement: float
    applied_by: str


class AlphawaveLearningAnalytics(BaseModel):
    """
    Learning analytics for sports prediction improvements.

    Attributes:
        user_id: User analytics are for
        sport: Sport being analyzed
        time_period: Analysis time period
        feedback_count: Number of feedback entries
        average_feedback_score: Average feedback rating
        most_common_feedback: Most frequent feedback type
        model_improvements: Number of model improvements made
        accuracy_trend: Accuracy improvement over time
        confidence_calibration: How well confidence matches accuracy
        recommendations: AI suggestions for improvement
        generated_at: When analytics were generated
    """

    user_id: UUID
    sport: str
    time_period: str  # "7d", "30d", "90d", "1y"
    feedback_count: int
    average_feedback_score: float
    most_common_feedback: Optional[FeedbackType]
    model_improvements: int
    accuracy_trend: float
    confidence_calibration: float
    recommendations: List[str]
    generated_at: datetime

    class Config:
        from_attributes = True


class AlphawavePredictionFeedback(BaseModel):
    """
    Comprehensive feedback model for sports predictions.

    Combines multiple feedback types into a single assessment.
    """

    prediction_id: UUID
    user_id: UUID
    overall_satisfaction: float = Field(..., ge=0.0, le=1.0)
    accuracy_rating: float = Field(..., ge=0.0, le=1.0)
    confidence_rating: float = Field(..., ge=0.0, le=1.0)
    reasoning_quality: float = Field(..., ge=0.0, le=1.0)
    timing_appropriateness: float = Field(..., ge=0.0, le=1.0)
    would_use_again: bool
    comments: Optional[str] = None
    suggestions: Optional[str] = None

    class Config:
        from_attributes = True


class AlphawaveSportsMetrics(BaseModel):
    """
    Sports prediction performance metrics.

    Comprehensive metrics for tracking model performance across
    different sports, prediction types, and time periods.
    """

    # Overall performance
    total_predictions: int
    total_correct: int
    overall_accuracy: float
    average_confidence: float

    # By sport performance
    sport_performance: Dict[str, Dict[str, float]]

    # By prediction type performance
    type_performance: Dict[str, Dict[str, float]]

    # Profit/Loss metrics
    total_bet_amount: float
    total_payout: float
    net_profit_loss: float
    roi_percentage: float

    # Learning metrics
    feedback_incorporated: int
    model_adjustments: int
    accuracy_improvement: float

    # Time-based metrics
    best_day: Optional[str]
    worst_day: Optional[str]
    best_time: Optional[str]
    streak_current: int
    streak_best: int

    # Generated timestamp
    calculated_at: datetime

    class Config:
        from_attributes = True


# Example usage and validation
if __name__ == "__main__":
    # Example learning log entry
    learning_entry = AlphawaveSportsLearningLogCreate(
        prediction_id="12345678-1234-1234-1234-123456789012",
        feedback_type=FeedbackType.ACCURACY,
        feedback_value=0.8,
        user_comment="The prediction was mostly right but the spread was off by 3 points"
    )

    print(f"✅ Sports learning model validated: {learning_entry.feedback_type}")
    print(f"   Feedback value: {learning_entry.feedback_value}")
    print(f"   Comment: {learning_entry.user_comment}")

    # Example model performance
    performance = AlphawaveModelPerformance(
        model_name="claude-sonnet",
        sport="nfl",
        prediction_type="game_winner",
        total_predictions=100,
        correct_predictions=65,
        accuracy_rate=0.65,
        average_confidence=0.72,
        average_error=0.15,
        improvement_rate=0.05,
        last_updated=datetime.utcnow()
    )

    print(f"✅ Model performance: {performance.accuracy_rate:.1%} accuracy")
    print(f"   Improvement rate: {performance.improvement_rate:.1%} per month")
