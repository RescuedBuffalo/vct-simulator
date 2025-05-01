from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import uuid
from datetime import datetime

from app.api.models.database import Match, Team, Player, Round, RoundEvent

# Match operations
def create_match(db: Session, map_name: str, team_a: dict, team_b: dict) -> Match:
    """Create a new match with teams and players."""
    match_id = str(uuid.uuid4())
    
    # Create match
    db_match = Match(
        id=match_id,
        map_name=map_name,
        status="in_progress"
    )
    db.add(db_match)
    
    # Create teams
    team_a_db = Team(
        id=f"{match_id}_A",
        match_id=match_id,
        name=team_a["name"],
        side="A"
    )
    team_b_db = Team(
        id=f"{match_id}_B",
        match_id=match_id,
        name=team_b["name"],
        side="B"
    )
    db.add(team_a_db)
    db.add(team_b_db)
    
    # Create players for team A
    for i, player_stats in enumerate(team_a["players"]):
        player_id = f"A{i+1}"
        player = Player(
            id=f"{match_id}_{player_id}",
            match_id=match_id,
            team_id=team_a_db.id,
            name=f"{team_a['name']}_Player{i+1}",
            role=player_stats.get("role", "duelist"),
            aim_rating=player_stats.get("aim_rating", 50),
            reaction_time=player_stats.get("reaction_time", 200),
            movement_accuracy=player_stats.get("movement_accuracy", 0.5),
            spray_control=player_stats.get("spray_control", 0.5),
            clutch_iq=player_stats.get("clutch_iq", 0.5)
        )
        db.add(player)
    
    # Create players for team B
    for i, player_stats in enumerate(team_b["players"]):
        player_id = f"B{i+1}"
        player = Player(
            id=f"{match_id}_{player_id}",
            match_id=match_id,
            team_id=team_b_db.id,
            name=f"{team_b['name']}_Player{i+1}",
            role=player_stats.get("role", "duelist"),
            aim_rating=player_stats.get("aim_rating", 50),
            reaction_time=player_stats.get("reaction_time", 200),
            movement_accuracy=player_stats.get("movement_accuracy", 0.5),
            spray_control=player_stats.get("spray_control", 0.5),
            clutch_iq=player_stats.get("clutch_iq", 0.5)
        )
        db.add(player)
    
    db.commit()
    db.refresh(db_match)
    return db_match

def get_match(db: Session, match_id: str) -> Optional[Match]:
    """Get a match by ID."""
    return db.query(Match).filter(Match.id == match_id).first()

def update_match_score(db: Session, match_id: str, team_a_score: int, team_b_score: int) -> Match:
    """Update match scores."""
    match = get_match(db, match_id)
    if match:
        match.team_a_score = team_a_score
        match.team_b_score = team_b_score
        match.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(match)
    return match

# Round operations
def create_round(db: Session, match_id: str, round_number: int) -> Round:
    """Create a new round."""
    round_id = str(uuid.uuid4())
    db_round = Round(
        id=round_id,
        match_id=match_id,
        round_number=round_number,
        phase="buy",
        time_remaining=100.0
    )
    db.add(db_round)
    db.commit()
    db.refresh(db_round)
    return db_round

def update_round_state(db: Session, round_id: str, state: dict) -> Round:
    """Update round state."""
    round = db.query(Round).filter(Round.id == round_id).first()
    if round:
        for key, value in state.items():
            setattr(round, key, value)
        db.commit()
        db.refresh(round)
    return round

# Player operations
def get_player(db: Session, player_id: str) -> Optional[Player]:
    """Get a player by ID."""
    return db.query(Player).filter(Player.id == player_id).first()

def update_player_state(db: Session, player_id: str, state: dict) -> Player:
    """Update player state."""
    player = get_player(db, player_id)
    if player:
        for key, value in state.items():
            setattr(player, key, value)
        db.commit()
        db.refresh(player)
    return player

def assign_agent(db: Session, player_id: str, agent_name: str) -> Player:
    """Assign an agent to a player."""
    player = get_player(db, player_id)
    if player:
        player.agent = agent_name
        db.commit()
        db.refresh(player)
    return player

def assign_ai(db: Session, player_id: str, ai_type: str, skill_level: float) -> Player:
    """Assign AI configuration to a player."""
    player = get_player(db, player_id)
    if player:
        player.ai_type = ai_type
        player.ai_skill_level = skill_level
        db.commit()
        db.refresh(player)
    return player

# Event operations
def create_round_event(db: Session, round_id: str, event_type: str, data: dict) -> RoundEvent:
    """Create a new round event."""
    event = RoundEvent(
        id=str(uuid.uuid4()),
        round_id=round_id,
        event_type=event_type,
        timestamp=time_module.time(),
        data=data
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

def get_round_events(db: Session, round_id: str) -> List[RoundEvent]:
    """Get all events for a round."""
    return db.query(RoundEvent).filter(RoundEvent.round_id == round_id).all() 