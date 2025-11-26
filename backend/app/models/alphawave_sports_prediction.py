"""
Sports prediction models for Nicole V7 Sports Oracle.
Handles DFS predictions, betting picks, and sports analytics.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class SportType(str, Enum):
    """Supported sports for predictions."""
    NFL = "nfl"
    NBA = "nba"
    MLB = "mlb"
    NHL = "nhl"
    SOCCER = "soccer"
    TENNIS = "tennis"
    GOLF = "golf"


class PredictionType(str, Enum):
    """Types of sports predictions."""
    GAME_WINNER = "game_winner"
    POINT_SPREAD = "point_spread"
    OVER_UNDER = "over_under"
    PLAYER_PROPS = "player_props"
    DFS_LINEUP = "dfs_lineup"


class PredictionOutcome(str, Enum):
    """Prediction outcome status."""
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PENDING = "pending"
    VOIDED = "voided"


class AlphawaveSportsPrediction(BaseModel):
    """
    Sports prediction model for DFS and betting analytics.

    Attributes:
        id: Unique prediction identifier
        user_id: Owner of the prediction
        sport: Sport type (NFL, NBA, etc.)
        prediction_type: Type of prediction (game winner, spread, etc.)
        game_id: External game identifier
        home_team: Home team name
        away_team: Away team name
        prediction: JSON prediction data with confidence scores
        confidence_score: Overall confidence (0-1)
        reasoning: AI reasoning for the prediction
        model_used: AI model that generated prediction
        outcome: Actual outcome (correct/incorrect/pending)
        actual_result: Actual game result data
        bet_amount: Amount wagered (optional)
        payout: Amount won (optional)
        created_at: Prediction timestamp
        resolved_at: Resolution timestamp
    """

    id: UUID
    user_id: UUID
    sport: SportType
    prediction_type: PredictionType
    game_id: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    prediction: Dict[str, Any] = Field(..., description="Prediction data with picks and confidence")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in prediction")
    reasoning: Optional[str] = Field(None, description="AI reasoning for the prediction")
    model_used: str = Field(default="claude-sonnet", description="AI model used")
    outcome: Optional[PredictionOutcome] = None
    actual_result: Optional[Dict[str, Any]] = Field(None, description="Actual game result")
    bet_amount: Optional[float] = Field(None, ge=0.0, description="Amount wagered")
    payout: Optional[float] = Field(None, ge=0.0, description="Amount won")
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AlphawaveSportsPredictionCreate(BaseModel):
    """Model for creating new sports predictions."""

    sport: SportType
    prediction_type: PredictionType
    game_id: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    prediction: Dict[str, Any] = Field(..., description="Prediction data")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    model_used: str = "claude-sonnet"
    bet_amount: Optional[float] = Field(None, ge=0.0)

    @validator('prediction')
    def validate_prediction_structure(cls, v):
        """Validate prediction structure based on type."""
        required_keys = ['prediction', 'confidence']

        if not isinstance(v, dict):
            raise ValueError("Prediction must be a dictionary")

        for key in required_keys:
            if key not in v:
                raise ValueError(f"Prediction missing required key: {key}")

        return v


class AlphawaveSportsPredictionUpdate(BaseModel):
    """Model for updating sports predictions."""

    outcome: Optional[PredictionOutcome] = None
    actual_result: Optional[Dict[str, Any]] = None
    resolved_at: Optional[datetime] = None
    bet_amount: Optional[float] = Field(None, ge=0.0)
    payout: Optional[float] = Field(None, ge=0.0)


class AlphawaveSportsPredictionResponse(BaseModel):
    """Response model for sports prediction API endpoints."""

    id: UUID
    sport: SportType
    prediction_type: PredictionType
    home_team: Optional[str]
    away_team: Optional[str]
    prediction: Dict[str, Any]
    confidence_score: float
    reasoning: Optional[str]
    model_used: str
    outcome: Optional[PredictionOutcome]
    created_at: datetime
    profit_loss: Optional[float] = None

    class Config:
        from_attributes = True


class AlphawaveSportsDataCache(BaseModel):
    """
    Sports data cache model for API response storage.

    Attributes:
        id: Unique cache entry identifier
        sport: Sport type
        data_type: Type of data cached
        external_id: External API identifier
        data: Cached JSON data
        source_api: API source (ESPN, Odds API, etc.)
        collected_at: Cache timestamp
        expires_at: Cache expiration
    """

    id: UUID
    sport: SportType
    data_type: str
    external_id: Optional[str]
    data: Dict[str, Any]
    source_api: str
    collected_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlphawaveSportsDataCacheCreate(BaseModel):
    """Model for creating sports data cache entries."""

    sport: SportType
    data_type: str
    external_id: Optional[str] = None
    data: Dict[str, Any]
    source_api: str
    expires_at: Optional[datetime] = None


class AlphawaveSportsLearningLog(BaseModel):
    """
    Sports learning log for model improvement.

    Attributes:
        id: Unique learning entry
        prediction_id: Related prediction
        user_id: User who provided feedback
        feedback_type: Type of feedback given
        feedback_value: Numerical feedback score
        user_comment: Optional user comment
        model_adjustment: AI adjustment based on feedback
        applied: Whether adjustment was applied
        created_at: Feedback timestamp
    """

    id: UUID
    prediction_id: UUID
    user_id: UUID
    feedback_type: str
    feedback_value: float
    user_comment: Optional[str] = None
    model_adjustment: Optional[Dict[str, Any]] = None
    applied: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class AlphawaveSportsLearningLogCreate(BaseModel):
    """Model for creating sports learning entries."""

    prediction_id: UUID
    feedback_type: str
    feedback_value: float
    user_comment: Optional[str] = None


class AlphawaveSportsDashboard(BaseModel):
    """
    Sports dashboard data model.

    Attributes:
        user_id: Dashboard owner
        date: Dashboard date
        total_predictions: Number of predictions made
        correct_predictions: Number correct
        accuracy_rate: Accuracy percentage
        total_bet_amount: Total money wagered
        total_payout: Total money won
        profit_loss: Net profit/loss
        top_sports: Most active sports
        recent_performance: Recent prediction performance
        upcoming_games: Games with predictions
        confidence_trends: Confidence score trends
        last_updated: Dashboard update timestamp
    """

    user_id: UUID
    date: datetime.date
    total_predictions: int
    correct_predictions: int
    accuracy_rate: float
    total_bet_amount: Optional[float]
    total_payout: Optional[float]
    profit_loss: Optional[float]
    top_sports: List[str]
    recent_performance: Dict[str, Any]
    upcoming_games: List[Dict[str, Any]]
    confidence_trends: Dict[str, Any]
    last_updated: datetime

    class Config:
        from_attributes = True


class AlphawaveSportsStats(BaseModel):
    """Sports statistics and performance metrics."""

    total_predictions: int
    total_correct: int
    total_incorrect: int
    accuracy_rate: float
    average_confidence: float
    profit_loss: float
    best_sport: Optional[str]
    worst_sport: Optional[str]
    most_active_day: Optional[str]
    total_bet_amount: float
    total_payout: float
    roi_percentage: float

    class Config:
        from_attributes = True


# Example usage and validation
if __name__ == "__main__":
    # Example sports prediction
    prediction = AlphawaveSportsPredictionCreate(
        sport=SportType.NFL,
        prediction_type=PredictionType.GAME_WINNER,
        game_id="20241201001",
        home_team="Chiefs",
        away_team="Raiders",
        prediction={
            "prediction": "Chiefs",
            "confidence": 0.75,
            "spread": -7.5,
            "over_under": 45.5
        },
        confidence_score=0.75,
        reasoning="Chiefs have strong home record and Raiders struggling on road",
        bet_amount=50.0
    )

    print(f"✅ Sports prediction model validated: {prediction.sport} - {prediction.prediction_type}")
    print(f"   Confidence: {prediction.confidence_score}")
    print(f"   Bet amount: ${prediction.bet_amount}")
