from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.api.database import Base

class Match(Base):
    __tablename__ = "matches"

    id = Column(String, primary_key=True, index=True)
    map_name = Column(String)
    team_a_score = Column(Integer, default=0)
    team_b_score = Column(Integer, default=0)
    current_round = Column(Integer, default=1)
    is_overtime = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="in_progress")  # in_progress, completed, cancelled
    
    # Relationships
    teams = relationship("Team", back_populates="match")
    rounds = relationship("Round", back_populates="match")
    players = relationship("Player", back_populates="match")

class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True, index=True)
    match_id = Column(String, ForeignKey("matches.id"))
    name = Column(String)
    side = Column(String)  # "A" or "B"
    score = Column(Integer, default=0)
    
    # Relationships
    match = relationship("Match", back_populates="teams")
    players = relationship("Player", back_populates="team")

class Player(Base):
    __tablename__ = "players"

    id = Column(String, primary_key=True, index=True)
    match_id = Column(String, ForeignKey("matches.id"))
    team_id = Column(String, ForeignKey("teams.id"))
    name = Column(String)
    agent = Column(String)
    role = Column(String)
    
    # Player stats
    aim_rating = Column(Float)
    reaction_time = Column(Float)
    movement_accuracy = Column(Float)
    spray_control = Column(Float)
    clutch_iq = Column(Float)
    
    # Current state
    health = Column(Integer, default=100)
    armor = Column(Integer, default=0)
    credits = Column(Integer, default=800)
    weapon = Column(String)
    shield = Column(String)
    alive = Column(Boolean, default=True)
    location = Column(JSON)  # Store as JSON: [x, y, z]
    
    # AI configuration
    ai_type = Column(String)
    ai_skill_level = Column(Float)
    
    # Match statistics
    kills = Column(Integer, default=0)
    deaths = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    
    # Relationships
    match = relationship("Match", back_populates="players")
    team = relationship("Team", back_populates="players")

class Round(Base):
    __tablename__ = "rounds"

    id = Column(String, primary_key=True, index=True)
    match_id = Column(String, ForeignKey("matches.id"))
    round_number = Column(Integer)
    phase = Column(String)  # buy, round, end
    time_remaining = Column(Float)
    spike_planted = Column(Boolean, default=False)
    spike_time_remaining = Column(Float)
    winner = Column(String)  # attackers, defenders
    end_condition = Column(String)
    
    # Relationships
    match = relationship("Match", back_populates="rounds")
    events = relationship("RoundEvent", back_populates="round")

class RoundEvent(Base):
    __tablename__ = "round_events"

    id = Column(String, primary_key=True, index=True)
    round_id = Column(String, ForeignKey("rounds.id"))
    event_type = Column(String)  # kill, plant, defuse, etc.
    timestamp = Column(Float)
    data = Column(JSON)  # Store event-specific data as JSON
    
    # Relationships
    round = relationship("Round", back_populates="events") 