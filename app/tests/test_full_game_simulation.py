import os
import random
import pytest
from app.simulation.models.player import Player
from app.simulation.models.team import Team
from app.simulation.models.round import Round
from app.simulation.models.match import Match
from app.simulation.models.map import generate_random_map, Map, MapBoundary
from app.simulation.ai_greedy import GreedyAgent
from json import load

class DummyAbility:
    def get_available_abilities(self):
        return []

@pytest.mark.slow
def test_full_valorant_game_simulation():
    # 1. Load the map data from JSON
    print(os.getcwd())
    map_data = load(open("/Users/aidankosik/workspace/vct-simulator/maps/ascent.map.json"))

    # 2. Create a Map object
    game_map = Map.from_json("/Users/aidankosik/workspace/vct-simulator/maps/ascent.map.json")

    # 3. Create 10 players with random stats
    roles = ["duelist", "controller", "sentinel", "initiator", "duelist"]
    agents = ["Jett", "Sage", "Phoenix", "Brimstone", "Viper", "Omen", "Sova", "Reyna", "Killjoy", "Cypher"]
    players = []
    for i in range(10):
        player = Player(
            id=f"P{i+1}",
            name=f"Player{i+1}",
            team_id="A" if i < 5 else "B",
            role=roles[i % 5],
            agent=agents[i],
            aim_rating=random.uniform(50, 100),
            reaction_time=random.uniform(150, 250),
            movement_accuracy=random.uniform(0.5, 1.0),
            spray_control=random.uniform(0.5, 1.0),
            clutch_iq=random.uniform(0.5, 1.0),
        )
        player.abilities = DummyAbility()
        players.append(player)

    # 4. Assign 5 to each team
    team_a_players = players[:5]
    team_b_players = players[5:]
    team_a = Team(id="A", name="Team A", players=team_a_players)
    team_b = Team(id="B", name="Team B", players=team_b_players)

    # 5. Wrap each Player in a GreedyAgent (not used directly, but would be in a real agent loop)
    agents_dict = {p.id: GreedyAgent(p) for p in players}

    # 6. Prepare player dict and team ids for Round
    player_dict = {p.id: p for p in players}
    attacker_ids = [p.id for p in team_a_players]
    defender_ids = [p.id for p in team_b_players]

    # 7. Create initial Round with the Map object
    round_obj = Round(
        round_number=1,
        players=player_dict,
        attacker_ids=attacker_ids,
        defender_ids=defender_ids,
        map_data=map_data,  # Keep for backward compatibility
        map_obj=game_map    # Pass the Map object
    )

    # 8. Create Match
    match = Match(
        map=game_map,
        round=round_obj,
        team_a=team_a,
        team_b=team_b
    )

    # 9. Run the match (this will simulate all rounds)
    match.run()

    # 10. Print or assert on the final score and stats
    print(f"Final Score: Team A {match.team_a_score} - Team B {match.team_b_score}")
    match.get_detailed_match_stats(write_to_file=True)
    match.stats.team_a_stats.get_summary(write_to_file=True)
    match.stats.team_b_stats.get_summary(write_to_file=True)
    for player_id, player_stats in match.stats.player_stats.items():
        player_stats.get_summary(write_to_file=True, name=player_id)
    assert match.team_a_score >= 0 and match.team_b_score >= 0
    assert match.team_a_score != match.team_b_score or match.is_overtime 