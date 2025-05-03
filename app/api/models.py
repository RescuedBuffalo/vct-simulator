from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

class TeamInfo(BaseModel):
    """Team information for match creation."""
    name: str
    players: List[Dict[str, float]] = Field(
        description="List of player stats dictionaries. Each dict should contain aim_rating, reaction_time, etc."
    )

class CreateMatchRequest(BaseModel):
    """Request model for creating a new match."""
    team_a: TeamInfo
    team_b: TeamInfo
    map_name: str
    agent_assignments: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional map of player_id to agent name"
    )

class MatchResponse(BaseModel):
    """Response model for match creation."""
    match_id: str
    status: str

class PlayerState(BaseModel):
    """Current state of a player."""
    id: str
    name: str
    team_id: str
    agent: str
    health: int
    armor: int
    credits: int
    weapon: Optional[str]
    shield: Optional[str]
    alive: bool
    location: Tuple[float, float, float]
    stats: Dict[str, int]

class RoundPhaseEnum(str, Enum):
    BUY = "buy"
    ROUND = "round"
    END = "end"

class RoundState(BaseModel):
    """Current state of a round."""
    round_number: int
    phase: RoundPhaseEnum
    time_remaining: float
    spike_planted: bool
    spike_time_remaining: Optional[float]
    alive_attackers: int
    alive_defenders: int
    winner: Optional[str]
    end_condition: Optional[str]

class MatchStateResponse(BaseModel):
    """Response model for match state."""
    match_id: str
    team_a_score: int
    team_b_score: int
    current_round: int
    is_overtime: bool
    players: Dict[str, PlayerState]
    current_round_state: RoundState

class RoundResponse(BaseModel):
    """Response model for round simulation."""
    round_number: int
    winner: str
    end_condition: str
    round_summary: Dict[str, Any]

class RoundStateResponse(BaseModel):
    """Response model for round state."""
    round_number: int
    state: RoundState
    events: List[Dict[str, Any]]

class AssignAgentRequest(BaseModel):
    """Request model for assigning an agent to a player."""
    agent_name: str

class AssignAIRequest(BaseModel):
    """Request model for assigning an AI to a player."""
    ai_type: str
    skill_level: float = Field(ge=0.0, le=1.0)

class PlayerResponse(BaseModel):
    """Response model for player updates."""
    player_id: str
    agent: Optional[str]
    ai_type: Optional[str]
    status: str

class MatchStatsResponse(BaseModel):
    """Response model for match statistics."""
    match_id: str
    duration: float
    team_a_score: int
    team_b_score: int
    rounds: List[Dict[str, Any]]
    player_stats: Dict[str, Dict[str, Any]]
    team_stats: Dict[str, Dict[str, Any]] 