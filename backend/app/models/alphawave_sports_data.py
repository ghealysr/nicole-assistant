"""
Sports data models for Nicole V7 Sports Oracle.
Handles caching of external API data (ESPN, Odds API, etc.).
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID
from enum import Enum


class SportType(str, Enum):
    """Supported sports for data collection."""
    NFL = "nfl"
    NBA = "nba"
    MLB = "mlb"
    NHL = "nhl"
    SOCCER = "soccer"
    TENNIS = "tennis"
    GOLF = "golf"


class DataType(str, Enum):
    """Types of sports data to cache."""
    GAMES = "games"
    PLAYERS = "players"
    TEAMS = "teams"
    ODDS = "odds"
    WEATHER = "weather"
    INJURIES = "injuries"
    STATS = "stats"
    SCHEDULE = "schedule"


class SourceAPI(str, Enum):
    """External API sources for sports data."""
    ESPN = "espn"
    THE_ODDS_API = "the_odds_api"
    WEATHER_API = "weather_api"
    SPORTS_DATA_IO = "sports_data_io"


class AlphawaveSportsDataCache(BaseModel):
    """
    Sports data cache model for storing external API responses.

    This enables efficient caching of expensive API calls while maintaining
    data freshness and avoiding rate limits.

    Attributes:
        id: Unique cache entry identifier
        sport: Sport type
        data_type: Type of data cached
        external_id: External API identifier (game ID, player ID, etc.)
        data: Cached JSON data from external API
        source_api: Which API provided the data
        collected_at: When data was cached
        expires_at: When cache entry expires
    """

    id: UUID
    sport: SportType
    data_type: DataType
    external_id: Optional[str] = None
    data: Dict[str, Any] = Field(..., description="Cached API response data")
    source_api: SourceAPI
    collected_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AlphawaveSportsDataCacheCreate(BaseModel):
    """Model for creating sports data cache entries."""

    sport: SportType
    data_type: DataType
    external_id: Optional[str] = None
    data: Dict[str, Any]
    source_api: SourceAPI
    expires_at: Optional[datetime] = None

    @validator('expires_at', pre=True, always=True)
    def set_default_expiry(cls, v, values):
        """Set default expiry based on data type if not provided."""
        if v is None:
            # Different expiry times based on data type
            expiry_map = {
                DataType.ODDS: timedelta(hours=1),  # Odds change frequently
                DataType.WEATHER: timedelta(hours=2),  # Weather updates hourly
                DataType.INJURIES: timedelta(hours=6),  # Injury updates throughout day
                DataType.GAMES: timedelta(hours=24),  # Game data stable for a day
                DataType.PLAYERS: timedelta(days=7),  # Player data stable for week
                DataType.TEAMS: timedelta(days=7),  # Team data stable for week
                DataType.STATS: timedelta(days=30),  # Stats don't change often
                DataType.SCHEDULE: timedelta(days=90),  # Schedules set far in advance
            }
            data_type = values.get('data_type')
            if data_type:
                return datetime.utcnow() + expiry_map.get(data_type, timedelta(hours=24))
        return v


class AlphawaveSportsDataCacheUpdate(BaseModel):
    """Model for updating sports data cache entries."""

    data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class AlphawaveGameData(BaseModel):
    """Structured model for game data from external APIs."""

    game_id: str
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    game_status: str  # scheduled, live, final, postponed, cancelled
    start_time: datetime
    venue: Optional[str] = None
    weather: Optional[Dict[str, Any]] = None
    odds: Optional[Dict[str, Any]] = None
    injuries: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class AlphawavePlayerData(BaseModel):
    """Structured model for player data."""

    player_id: str
    name: str
    team: str
    position: Optional[str] = None
    stats: Dict[str, Any] = Field(default_factory=dict)
    status: str = "active"  # active, injured, suspended, retired
    last_updated: datetime

    class Config:
        from_attributes = True


class AlphawaveTeamData(BaseModel):
    """Structured model for team data."""

    team_id: str
    name: str
    city: str
    sport: SportType
    record: Optional[Dict[str, Any]] = None
    standings: Optional[Dict[str, Any]] = None
    roster: Optional[List[str]] = None  # Player IDs
    last_updated: datetime

    class Config:
        from_attributes = True


class AlphawaveOddsData(BaseModel):
    """Structured model for betting odds data."""

    game_id: str
    sportsbook: str
    spread: Optional[float] = None
    spread_odds: Optional[int] = None
    over_under: Optional[float] = None
    over_under_odds: Optional[int] = None
    moneyline_home: Optional[int] = None
    moneyline_away: Optional[int] = None
    last_updated: datetime

    class Config:
        from_attributes = True


class AlphawaveWeatherData(BaseModel):
    """Structured model for game weather conditions."""

    game_id: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    precipitation: Optional[str] = None  # rain, snow, clear, etc.
    conditions: str  # clear, cloudy, rain, snow, etc.
    last_updated: datetime

    class Config:
        from_attributes = True


class AlphawaveInjuryData(BaseModel):
    """Structured model for player injury information."""

    player_id: str
    injury_type: str
    severity: str  # minor, moderate, major, season-ending
    expected_return: Optional[datetime] = None
    status: str  # questionable, doubtful, out, ir
    description: Optional[str] = None
    last_updated: datetime

    class Config:
        from_attributes = True


class AlphawaveSportsAPIResponse(BaseModel):
    """Generic response model for sports API endpoints."""

    success: bool
    data: Any
    cached: bool = False
    cache_expires: Optional[datetime] = None
    source: Optional[SourceAPI] = None

    class Config:
        from_attributes = True


# Example usage and validation
if __name__ == "__main__":
    # Example game data cache
    game_data = AlphawaveSportsDataCacheCreate(
        sport=SportType.NFL,
        data_type=DataType.GAMES,
        external_id="20241201001",
        data={
            "game_id": "20241201001",
            "home_team": "Chiefs",
            "away_team": "Raiders",
            "start_time": "2024-12-01T13:00:00Z",
            "status": "scheduled"
        },
        source_api=SourceAPI.ESPN
    )

    print(f"✅ Sports data cache model validated: {game_data.sport} - {game_data.data_type}")
    print(f"   External ID: {game_data.external_id}")
    print(f"   Expires: {game_data.expires_at}")

    # Example odds data
    odds_data = AlphawaveOddsData(
        game_id="20241201001",
        sportsbook="DraftKings",
        spread=-7.5,
        spread_odds=-110,
        over_under=45.5,
        over_under_odds=-110,
        moneyline_home=-350,
        moneyline_away=285,
        last_updated=datetime.utcnow()
    )

    print(f"✅ Odds data model validated: {odds_data.spread} spread")
    print(f"   Moneyline: Home {odds_data.moneyline_home}, Away {odds_data.moneyline_away}")
