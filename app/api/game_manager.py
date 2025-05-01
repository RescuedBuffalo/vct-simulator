import uuid
from typing import Dict, List, Optional
import os
import json

from app.simulation.models.match import Match
from app.simulation.models.player import Player
from app.simulation.models.team import Team
from app.simulation.models.round import Round
from app.simulation.models.map import Map
from app.simulation.ai.agents.base import AgentConfig
from app.simulation.ai.agents.greedy import GreedyAgent
from app.simulation.ai.inference.agent_pool import AgentPool

class GameManager:
    def __init__(self):
        """Initialize the game manager."""
        self.matches: Dict[str, Match] = {}
        self.agent_pool = AgentPool()
        self.agent_pool.register_agent_class('greedy', GreedyAgent)
        
        # Load available maps
        self.maps = self._load_maps()
        
        # Available agents and AI types
        self.available_agents = [
            "Jett", "Sage", "Phoenix", "Brimstone", "Viper",
            "Omen", "Sova", "Reyna", "Killjoy", "Cypher"
        ]
        self.available_ai_types = ["greedy"]  # Add more as implemented

    def _load_maps(self) -> Dict[str, Map]:
        """Load all available maps."""
        maps_dir = os.path.join(os.path.dirname(__file__), '../../maps')
        maps = {}
        for filename in os.listdir(maps_dir):
            if filename.endswith('.map.json'):
                map_name = filename.replace('.map.json', '')
                with open(os.path.join(maps_dir, filename)) as f:
                    map_data = json.load(f)
                    maps[map_name] = Map.from_json(map_data)
        return maps

    def create_match(self, team_a: dict, team_b: dict, map_name: str, 
                    agent_assignments: Optional[Dict[str, str]] = None) -> str:
        """Create a new match."""
        if map_name not in self.maps:
            raise ValueError(f"Map {map_name} not found")

        # Create players for team A
        team_a_players = []
        for i, player_stats in enumerate(team_a["players"]):
            player_id = f"A{i+1}"
            player = Player(
                id=player_id,
                name=f"{team_a['name']}_Player{i+1}",
                team_id="A",
                role=player_stats.get("role", "duelist"),
                agent=agent_assignments.get(player_id, ""),
                aim_rating=player_stats.get("aim_rating", 50),
                reaction_time=player_stats.get("reaction_time", 200),
                movement_accuracy=player_stats.get("movement_accuracy", 0.5),
                spray_control=player_stats.get("spray_control", 0.5),
                clutch_iq=player_stats.get("clutch_iq", 0.5)
            )
            team_a_players.append(player)

        # Create players for team B
        team_b_players = []
        for i, player_stats in enumerate(team_b["players"]):
            player_id = f"B{i+1}"
            player = Player(
                id=player_id,
                name=f"{team_b['name']}_Player{i+1}",
                team_id="B",
                role=player_stats.get("role", "duelist"),
                agent=agent_assignments.get(player_id, ""),
                aim_rating=player_stats.get("aim_rating", 50),
                reaction_time=player_stats.get("reaction_time", 200),
                movement_accuracy=player_stats.get("movement_accuracy", 0.5),
                spray_control=player_stats.get("spray_control", 0.5),
                clutch_iq=player_stats.get("clutch_iq", 0.5)
            )
            team_b_players.append(player)

        # Create teams
        team_a_obj = Team(id="A", name=team_a["name"], players=team_a_players)
        team_b_obj = Team(id="B", name=team_b["name"], players=team_b_players)

        # Create player dictionary and team IDs for Round
        players = {p.id: p for p in team_a_players + team_b_players}
        attacker_ids = [p.id for p in team_a_players]
        defender_ids = [p.id for p in team_b_players]

        # Create initial Round
        round_obj = Round(
            round_number=1,
            players=players,
            attacker_ids=attacker_ids,
            defender_ids=defender_ids,
            map_obj=self.maps[map_name]
        )

        # Create Match
        match = Match(
            map=self.maps[map_name],
            round=round_obj,
            team_a=team_a_obj,
            team_b=team_b_obj
        )

        # Generate match ID and store match
        match_id = str(uuid.uuid4())
        self.matches[match_id] = match
        return match_id

    def get_match_state(self, match_id: str) -> dict:
        """Get the current state of a match."""
        match = self._get_match(match_id)
        return {
            "match_id": match_id,
            "team_a_score": match.team_a_score,
            "team_b_score": match.team_b_score,
            "current_round": match.current_round,
            "is_overtime": match.is_overtime,
            "players": self._get_player_states(match),
            "current_round_state": self._get_round_state(match.round)
        }

    def simulate_next_round(self, match_id: str) -> dict:
        """Simulate the next round of the match."""
        match = self._get_match(match_id)
        round_result = match.round.simulate()
        return {
            "round_number": match.current_round,
            "winner": round_result["winner"],
            "end_condition": round_result["end_condition"],
            "round_summary": round_result
        }

    def get_round_state(self, match_id: str, round_number: int) -> dict:
        """Get the state of a specific round."""
        match = self._get_match(match_id)
        if round_number > match.current_round:
            raise KeyError(f"Round {round_number} has not been played yet")
        round_state = match.round_results.get(round_number)
        if not round_state:
            raise KeyError(f"Round {round_number} not found")
        return {
            "round_number": round_number,
            "state": round_state,
            "events": self._get_round_events(match, round_number)
        }

    def assign_agent(self, match_id: str, player_id: str, agent_name: str) -> dict:
        """Assign an agent to a player."""
        if agent_name not in self.available_agents:
            raise ValueError(f"Agent {agent_name} not available")
        match = self._get_match(match_id)
        player = self._get_player(match, player_id)
        player.agent = agent_name
        return {
            "player_id": player_id,
            "agent": agent_name,
            "ai_type": None,
            "status": "updated"
        }

    def assign_ai_agent(self, match_id: str, player_id: str, ai_type: str, skill_level: float) -> dict:
        """Assign an AI agent to a player."""
        if ai_type not in self.available_ai_types:
            raise ValueError(f"AI type {ai_type} not available")
        match = self._get_match(match_id)
        player = self._get_player(match, player_id)
        
        # Create AI agent
        agent = self.agent_pool.get_agent(
            role=player.role,
            skill_level=skill_level,
            agent_type=ai_type
        )
        
        # Store AI agent in match's agents_dict
        if not hasattr(match, 'agents_dict'):
            match.agents_dict = {}
        match.agents_dict[player_id] = agent
        
        return {
            "player_id": player_id,
            "agent": player.agent,
            "ai_type": ai_type,
            "status": "updated"
        }

    def get_available_maps(self) -> List[str]:
        """Get a list of available maps."""
        return list(self.maps.keys())

    def get_available_agents(self) -> List[str]:
        """Get a list of available agents."""
        return self.available_agents

    def get_available_ai_types(self) -> List[str]:
        """Get a list of available AI agent types."""
        return self.available_ai_types

    def get_match_stats(self, match_id: str) -> dict:
        """Get detailed statistics for a match."""
        match = self._get_match(match_id)
        return match.stats.get_match_summary()

    def _get_match(self, match_id: str) -> Match:
        """Get a match by ID."""
        if match_id not in self.matches:
            raise KeyError(f"Match {match_id} not found")
        return self.matches[match_id]

    def _get_player(self, match: Match, player_id: str) -> Player:
        """Get a player from a match."""
        for player in match.team_a.players + match.team_b.players:
            if player.id == player_id:
                return player
        raise KeyError(f"Player {player_id} not found")

    def _get_player_states(self, match: Match) -> Dict[str, dict]:
        """Get the current state of all players in a match."""
        states = {}
        for player in match.team_a.players + match.team_b.players:
            states[player.id] = {
                "id": player.id,
                "name": player.name,
                "team_id": player.team_id,
                "agent": player.agent,
                "health": player.health,
                "armor": player.armor,
                "credits": player.creds,
                "weapon": player.weapon.name if player.weapon else None,
                "shield": player.shield,
                "alive": player.alive,
                "location": player.location,
                "stats": {
                    "kills": player.kills,
                    "deaths": player.deaths,
                    "assists": player.assists
                }
            }
        return states

    def _get_round_state(self, round_obj: Round) -> dict:
        """Get the current state of a round."""
        return {
            "round_number": round_obj.round_number,
            "phase": round_obj.phase.value,
            "time_remaining": round_obj.round_time_remaining,
            "spike_planted": round_obj.spike_planted,
            "spike_time_remaining": round_obj.spike_time_remaining,
            "alive_attackers": len([p for p in round_obj.players.values() if p.id in round_obj.attacker_ids and p.alive]),
            "alive_defenders": len([p for p in round_obj.players.values() if p.id in round_obj.defender_ids and p.alive]),
            "winner": round_obj.round_winner.value if round_obj.round_winner else None,
            "end_condition": round_obj.round_end_condition.value if round_obj.round_end_condition else None
        }

    def _get_round_events(self, match: Match, round_number: int) -> List[dict]:
        """Get all events that occurred in a round."""
        # This would include kills, plants, defuses, etc.
        # Implementation depends on how events are stored in the Round class
        return []  # Placeholder - implement based on actual event tracking 