from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import uuid

from app.api.models import *
from app.api.game_manager import GameManager

app = FastAPI(title="VCT Simulator API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize game manager
game_manager = GameManager()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "VCT Simulator API is running"}

@app.post("/matches/", response_model=MatchResponse)
async def create_match(request: CreateMatchRequest):
    """Create a new match with specified teams and map."""
    try:
        match_id = game_manager.create_match(
            team_a=request.team_a,
            team_b=request.team_b,
            map_name=request.map_name,
            agent_assignments=request.agent_assignments
        )
        return {"match_id": match_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/matches/{match_id}", response_model=MatchStateResponse)
async def get_match_state(match_id: str):
    """Get the current state of a match."""
    try:
        return game_manager.get_match_state(match_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match not found")

@app.post("/matches/{match_id}/rounds/next", response_model=RoundResponse)
async def simulate_next_round(match_id: str):
    """Simulate the next round of the match."""
    try:
        return game_manager.simulate_next_round(match_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/matches/{match_id}/rounds/{round_number}", response_model=RoundStateResponse)
async def get_round_state(match_id: str, round_number: int):
    """Get the state of a specific round."""
    try:
        return game_manager.get_round_state(match_id, round_number)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match or round not found")

@app.post("/matches/{match_id}/players/{player_id}/agent", response_model=PlayerResponse)
async def assign_agent(match_id: str, player_id: str, request: AssignAgentRequest):
    """Assign an agent to a player."""
    try:
        return game_manager.assign_agent(match_id, player_id, request.agent_name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match or player not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/matches/{match_id}/players/{player_id}/ai", response_model=PlayerResponse)
async def assign_ai(match_id: str, player_id: str, request: AssignAIRequest):
    """Assign an AI agent to a player."""
    try:
        return game_manager.assign_ai_agent(match_id, player_id, request.ai_type, request.skill_level)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match or player not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/maps/", response_model=List[str])
async def list_maps():
    """Get a list of available maps."""
    return game_manager.get_available_maps()

@app.get("/agents/", response_model=List[str])
async def list_agents():
    """Get a list of available agents."""
    return game_manager.get_available_agents()

@app.get("/ai_types/", response_model=List[str])
async def list_ai_types():
    """Get a list of available AI agent types."""
    return game_manager.get_available_ai_types()

@app.get("/matches/{match_id}/stats", response_model=MatchStatsResponse)
async def get_match_stats(match_id: str):
    """Get detailed statistics for a match."""
    try:
        return game_manager.get_match_stats(match_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match not found") 