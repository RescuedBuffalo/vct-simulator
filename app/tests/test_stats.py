import pytest
from app.simulation.models.player_stats import PlayerMatchStats
from app.simulation.models.team_stats import EnhancedTeamStats
from app.simulation.models.match_stats import MatchStats
from typing import Dict, List, Tuple


def test_player_stats_basic_initialization():
    """Test basic initialization of PlayerMatchStats."""
    stats = PlayerMatchStats()
    assert stats.kills == 0
    assert stats.deaths == 0
    assert stats.assists == 0
    assert stats.damage_dealt == 0
    assert stats.headshots == 0
    assert stats.first_bloods == 0
    assert stats.first_deaths == 0
    assert stats.average_combat_score == 0.0


def test_player_stats_kill_tracking():
    """Test kill tracking and related stats."""
    stats = PlayerMatchStats()
    # Record a regular kill
    stats.record_kill(
        weapon="Vandal",
        is_headshot=False,
        position=(100.0, 100.0),
        is_first_blood=False,
        is_wallbang=False
    )
    assert stats.kills == 1
    assert stats.weapon_kills.get("Vandal") == 1
    assert stats.headshots == 0
    
    # Record a headshot kill
    stats.record_kill(
        weapon="Vandal",
        is_headshot=True,
        position=(100.0, 200.0),
        is_first_blood=False,
        is_wallbang=False
    )
    assert stats.kills == 2
    assert stats.weapon_kills.get("Vandal") == 2
    assert stats.headshots == 1
    assert stats.weapon_headshots.get("Vandal") == 1
    
    # Record a first blood kill
    stats.record_kill(
        weapon="Sheriff",
        is_headshot=True,
        position=(150.0, 150.0),
        is_first_blood=True,
        is_wallbang=False
    )
    assert stats.kills == 3
    assert stats.first_bloods == 1
    assert stats.weapon_kills.get("Sheriff") == 1
    assert stats.headshots == 2
    assert stats.weapon_headshots.get("Sheriff") == 1


def test_player_stats_damage_tracking():
    """Test damage tracking and related stats."""
    stats = PlayerMatchStats()
    
    # Record body damage
    stats.record_damage(
        damage=78,
        weapon="Phantom",
        is_bodyshot=True
    )
    assert stats.damage_dealt == 78
    assert stats.bodyshots == 1
    assert stats.weapon_damage.get("Phantom") == 78
    
    # Record headshot damage
    stats.record_damage(
        damage=156,
        weapon="Phantom",
        is_headshot=True
    )
    assert stats.damage_dealt == 78 + 156
    assert stats.headshots == 1
    assert stats.weapon_damage.get("Phantom") == 78 + 156
    
    # Record utility damage
    stats.record_damage(
        damage=50,
        weapon="Molly",
        is_utility=True
    )
    assert stats.damage_dealt == 78 + 156 + 50
    assert stats.damage_by_utility == 50


def test_player_stats_ratio_calculations():
    """Test calculation of KD ratio, headshot percentage, etc."""
    stats = PlayerMatchStats()
    stats.kills = 15
    stats.deaths = 5
    stats.assists = 2
    stats.headshots = 6
    stats.rounds_played = 20
    stats.damage_dealt = 2500
    stats.first_bloods = 3
    
    # Update ratios
    stats.update_ratios()
    
    # Check KDA
    assert stats.kill_death_assist_ratio == (stats.kills + stats.assists) / stats.deaths
    assert stats.kill_death_assist_ratio == 3.4
    
    # Check HS%
    assert stats.get_headshot_percentage() == (stats.headshots / stats.kills) * 100
    assert stats.get_headshot_percentage() == 40.0
    
    # Check ADR
    assert stats.damage_per_round == stats.damage_dealt / stats.rounds_played
    assert stats.damage_per_round == 125.0
    
    # Check KPR
    assert stats.kills_per_round == stats.kills / stats.rounds_played
    assert stats.kills_per_round == 0.75
    
    # Check ACS formula
    expected_acs = ((stats.damage_dealt / stats.rounds_played) + 
                    (50 * stats.kills / stats.rounds_played) +
                    (25 * stats.assists / stats.rounds_played) +
                    (33 * stats.first_bloods / stats.rounds_played))
    assert stats.average_combat_score == pytest.approx(expected_acs)


def test_player_stats_round_recording():
    """Test recording round-by-round performance."""
    stats = PlayerMatchStats()
    
    # Record first round
    stats.record_round_stats(
        round_number=1,
        kills=2,
        deaths=1,
        damage=200,
        credits_earned=2400,
        side="attack",
        won_round=True
    )
    assert stats.rounds_played == 1
    assert stats.rounds_with_kills == 1
    assert stats.rounds_with_deaths == 1
    assert stats.rounds_with_damage == 1
    assert stats.credits_earned == 2400
    assert len(stats.round_performance) == 1
    
    # Record second round
    stats.record_round_stats(
        round_number=2,
        kills=0,
        deaths=1,
        damage=50,
        credits_earned=1900,
        side="attack",
        won_round=False
    )
    assert stats.rounds_played == 2
    assert stats.rounds_with_kills == 1  # unchanged
    assert stats.rounds_with_deaths == 2
    assert stats.rounds_with_damage == 2
    assert stats.credits_earned == 2400 + 1900
    assert len(stats.round_performance) == 2


def test_player_stats_summary():
    """Test generation of player stats summary."""
    stats = PlayerMatchStats()
    stats.kills = 20
    stats.deaths = 10
    stats.assists = 5
    stats.headshots = 8
    stats.average_combat_score = 250.5
    stats.damage_per_round = 160.3
    stats.first_bloods = 3
    stats.clutches = 2
    stats.clutches_attempted = 4
    stats.entry_success = 2
    stats.entry_attempts = 5
    stats.damage_by_utility = 120
    stats.eco_kills = 6
    stats.eco_deaths = 1
    
    summary = stats.get_summary()
    
    assert summary["kda"] == "20/10/5"
    assert summary["kd_ratio"] == 2.5
    assert summary["acs"] == 250.5
    assert summary["adr"] == 160.3
    assert summary["hs_percentage"] == 40.0
    assert summary["first_bloods"] == 3
    assert summary["clutches"] == "2/4"
    assert summary["entry_success"] == "2/5"
    assert summary["utility_damage"] == 120
    assert summary["eco_impact"] == 5  # eco_kills - eco_deaths


def test_team_stats_initialization():
    """Test initialization of EnhancedTeamStats."""
    stats = EnhancedTeamStats()
    assert stats.rounds_won == 0
    assert stats.rounds_lost == 0
    assert stats.attack_rounds_won == 0
    assert stats.defense_rounds_won == 0
    assert stats.first_bloods == 0
    assert stats.clutches == 0
    assert stats.clutches_attempted == 0
    assert stats.flawless_rounds == 0
    assert stats.thrifty_rounds == 0


def test_team_stats_round_recording():
    """Test recording round results for a team."""
    stats = EnhancedTeamStats()
    
    # Record a won attack round
    stats.record_round_result(
        round_number=1,
        won=True,
        side="attack",
        equipment_value=15000,
        enemies_alive=0,
        time_remaining=45.5,
        score_difference=0,
        end_condition="elimination",
        site="A"
    )
    assert stats.rounds_won == 1
    assert stats.attack_rounds_won == 1
    assert stats.consecutive_rounds_won == 1
    assert stats.flawless_rounds == 1  # enemies_alive=0
    
    # Record a lost attack round
    stats.record_round_result(
        round_number=2,
        won=False,
        side="attack",
        equipment_value=16000,
        enemies_alive=2,
        time_remaining=20.0,
        score_difference=-1,
        end_condition="elimination",
        site=None
    )
    assert stats.rounds_won == 1
    assert stats.rounds_lost == 1
    assert stats.consecutive_rounds_won == 0  # reset after loss
    
    # Record a won defense round
    stats.record_round_result(
        round_number=3,
        won=True,
        side="defense",
        equipment_value=12000,
        enemies_alive=1,
        time_remaining=0.0,
        score_difference=0,
        end_condition="time_expired",
        site=None
    )
    assert stats.rounds_won == 2
    assert stats.defense_rounds_won == 1
    assert stats.consecutive_rounds_won == 1
    
    # Record a thrifty win (low equipment value)
    stats.record_round_result(
        round_number=4,
        won=True,
        side="defense",
        equipment_value=5000,  # thrifty threshold is 7000
        enemies_alive=0,
        time_remaining=30.0,
        score_difference=1,
        end_condition="elimination",
        site=None
    )
    assert stats.rounds_won == 3
    assert stats.defense_rounds_won == 2
    assert stats.consecutive_rounds_won == 2
    assert stats.flawless_rounds == 2
    assert stats.thrifty_rounds == 1
    
    # Record a comeback round (down by 4+ rounds)
    stats.record_round_result(
        round_number=5,
        won=True,
        side="attack",
        equipment_value=14000,
        enemies_alive=1,
        time_remaining=25.0,
        score_difference=-4,  # comeback threshold
        end_condition="spike_detonation",
        site="B"
    )
    assert stats.rounds_won == 4
    assert stats.attack_rounds_won == 2
    assert stats.consecutive_rounds_won == 3
    assert stats.max_consecutive_rounds_won == 3
    assert stats.comeback_rounds == 1
    assert stats.plants_by_site.get("B") == 1

    
def test_team_stats_from_player_stats():
    """Test updating team stats from player stats."""
    team_stats = EnhancedTeamStats()
    
    # Create some player stats
    player1 = PlayerMatchStats()
    player1.kills = 15
    player1.deaths = 10
    player1.assists = 3
    player1.damage_dealt = 2000
    player1.headshots = 6
    player1.first_bloods = 2
    player1.first_deaths = 1
    player1.clutches = 1
    player1.clutches_attempted = 2
    player1.damage_by_utility = 150
    player1.enemies_flashed = 5
    player1.teammates_flashed = 1
    player1.utilities_used = {"flash": 3, "smoke": 2}
    player1.weapons_purchased = {"Vandal": 2, "Sheriff": 1}
    player1.multi_kills = {"2k": 2, "3k": 1, "4k": 0, "5k": 0}
    player1.average_combat_score = 240.0
    
    player2 = PlayerMatchStats()
    player2.kills = 10
    player2.deaths = 5
    player2.assists = 7
    player2.damage_dealt = 1500
    player2.headshots = 4
    player2.first_bloods = 1
    player2.first_deaths = 2
    player2.clutches = 0
    player2.clutches_attempted = 1
    player2.damage_by_utility = 100
    player2.enemies_flashed = 3
    player2.teammates_flashed = 2
    player2.utilities_used = {"flash": 2, "smoke": 3}
    player2.weapons_purchased = {"Phantom": 3}
    player2.multi_kills = {"2k": 1, "3k": 0, "4k": 0, "5k": 0}
    player2.average_combat_score = 200.0
    
    # Update team stats
    player_stats = {"player1": player1, "player2": player2}
    team_stats.update_from_player_stats(player_stats, total_rounds=10)
    
    # Check aggregated stats
    assert team_stats.total_kills == 25
    assert team_stats.total_deaths == 15
    assert team_stats.total_assists == 10
    assert team_stats.total_damage_dealt == 3500
    assert team_stats.total_headshots == 10
    assert team_stats.first_bloods == 3
    assert team_stats.first_deaths == 3
    assert team_stats.clutches == 1
    assert team_stats.clutches_attempted == 3
    assert team_stats.utility_damage == 250
    assert team_stats.enemies_flashed == 8
    assert team_stats.teammates_flashed == 3
    assert team_stats.utility_used == {"flash": 5, "smoke": 5}
    assert team_stats.weapons_purchased == {"Vandal": 2, "Sheriff": 1, "Phantom": 3}
    assert team_stats.multi_kills == {"2k": 3, "3k": 1, "4k": 0, "5k": 0}
    assert team_stats.avg_combat_score == 220.0  # (240 + 200) / 2
    assert team_stats.avg_damage_per_round == 350.0  # 3500 / 10


def test_team_stats_summary():
    """Test generation of team stats summary."""
    stats = EnhancedTeamStats()
    stats.rounds_won = 13
    stats.rounds_lost = 7
    stats.attack_rounds_won = 7
    stats.defense_rounds_won = 6
    stats.first_bloods = 10
    stats.clutches = 3
    stats.clutches_attempted = 5
    stats.avg_damage_per_round = 350.0
    stats.total_kills = 100
    stats.total_headshots = 40
    stats.flawless_rounds = 4
    stats.thrifty_rounds = 1
    stats.multi_kills = {"2k": 10, "3k": 5, "4k": 2, "5k": 0}
    stats.trade_efficiency = 1.2
    stats.side_win_rates = {"attack": 0.6, "defense": 0.7}
    # Economy data
    stats.economy["eco_rounds_played"] = 3
    stats.economy["eco_rounds_won"] = 1
    stats.economy["bonus_rounds_played"] = 2
    stats.economy["bonus_rounds_won"] = 1
    stats.economy["full_buy_rounds"] = 15
    stats.economy["full_buy_rounds_won"] = 11
    # Site preferences
    stats.plants_by_site = {"A": 6, "B": 4, "C": 0}
    
    summary = stats.get_summary()
    
    assert summary["score"] == "13-7"
    assert summary["win_rate"] == 65.0
    assert summary["side_win_rates"]["attack"] == 60.0
    assert summary["side_win_rates"]["defense"] == 70.0
    assert summary["first_bloods"] == 10
    assert summary["clutches"] == "3/5"
    assert summary["avg_damage_per_round"] == 350.0
    assert summary["headshot_percentage"] == 40.0
    assert summary["flawless_rounds"] == 4
    assert summary["thrifty_rounds"] == 1
    assert summary["multi_kills"] == {"2k": 10, "3k": 5, "4k": 2, "5k": 0}
    assert summary["trade_efficiency"] == 1.2
    assert summary["eco_performance"]["eco"] == 33.3  # 1/3 * 100
    assert summary["eco_performance"]["bonus"] == 50.0  # 1/2 * 100
    assert summary["eco_performance"]["full_buy"] == 73.3  # 11/15 * 100
    assert summary["site_preferences"] == {"A": 60.0, "B": 40.0, "C": 0.0}


def test_integration_match_stats():
    """Integration test for MatchStats with player and team stats."""
    match_stats = MatchStats()
    
    # Initialize players
    player_a1_id = "a1"
    player_a2_id = "a2"
    player_b1_id = "b1"
    player_b2_id = "b2"
    
    match_stats.initialize_player(player_a1_id)
    match_stats.initialize_player(player_a2_id)
    match_stats.initialize_player(player_b1_id)
    match_stats.initialize_player(player_b2_id)
    
    # Record a kill
    match_stats.record_kill(
        round_number=1,
        time=15.5,
        killer_id=player_a1_id,
        victim_id=player_b1_id,
        weapon="Vandal",
        is_headshot=True,
        position=(100.0, 100.0),
        is_first_blood=True,
        killer_team="team_a",
        victim_team="team_b"
    )
    
    # Verify kill was recorded
    assert len(match_stats.kill_events) == 1
    assert match_stats.player_stats[player_a1_id].kills == 1
    assert match_stats.player_stats[player_a1_id].headshots == 1
    assert match_stats.player_stats[player_a1_id].first_bloods == 1
    assert match_stats.player_stats[player_b1_id].deaths == 1
    assert match_stats.player_stats[player_b1_id].first_deaths == 1
    
    # Record damage
    match_stats.record_damage(
        round_number=1,
        time=20.0,
        attacker_id=player_a2_id,
        victim_id=player_b2_id,
        damage=78,
        weapon="Phantom",
        hitbox="body",
        attacker_position=(110.0, 110.0),
        victim_position=(115.0, 115.0)
    )
    
    # Verify damage was recorded
    assert match_stats.player_stats[player_a2_id].damage_dealt == 78
    
    # Record spike plant
    match_stats.record_plant(
        round_number=1,
        time=30.0,
        planter_id=player_a1_id,
        site="A",
        position=(120.0, 120.0),
        team="team_a",
        remaining_defenders=1,
        time_elapsed=25.0
    )
    
    # Verify plant was recorded
    assert len(match_stats.plant_events) == 1
    assert match_stats.player_stats[player_a1_id].plants == 1
    assert match_stats.team_a_stats.plants == 1
    assert "A" in match_stats.team_a_stats.plants_by_site
    
    # Record round result
    match_stats.record_round_result(
        round_number=1,
        winner="team_a",
        end_condition="spike_detonation",
        site="A",
        time_remaining=0.0,
        team_a_alive=2,
        team_b_alive=0,
        team_a_equipment=14000,
        team_b_equipment=13000,
        team_a_side="attack",
        team_b_side="defense"
    )
    
    # Verify round result was recorded
    assert len(match_stats.round_results) == 1
    assert match_stats.team_a_stats.rounds_won == 1
    assert match_stats.team_b_stats.rounds_lost == 1
    assert match_stats.team_a_stats.attack_rounds_won == 1
    
    # Record another round with different outcome
    match_stats.record_kill(
        round_number=2,
        time=10.0,
        killer_id=player_b1_id,
        victim_id=player_a1_id,
        weapon="Vandal",
        is_headshot=False,
        position=(100.0, 100.0),
        is_first_blood=True,
        killer_team="team_b",
        victim_team="team_a"
    )
    
    match_stats.record_round_result(
        round_number=2,
        winner="team_b",
        end_condition="elimination",
        site=None,
        time_remaining=45.0,
        team_a_alive=0,
        team_b_alive=2,
        team_a_equipment=8000,
        team_b_equipment=13000,
        team_a_side="attack",
        team_b_side="defense"
    )
    
    # Verify updated stats
    assert match_stats.team_a_stats.rounds_won == 1
    assert match_stats.team_a_stats.rounds_lost == 1
    assert match_stats.team_b_stats.rounds_won == 1
    assert match_stats.team_b_stats.rounds_lost == 1
    
    # Finalize match
    match_stats.record_match_end(
        winner="team_a",
        final_score_a=13,
        final_score_b=11,
        match_duration=2400.0,
        total_rounds=24
    )
    
    # Get match summary
    summary = match_stats.get_match_summary()
    
    # Verify summary
    assert summary["winner"] == "team_a"
    assert summary["total_rounds"] == 24
    assert summary["duration"] == 2400.0
    assert "player_stats" in summary
    assert "team_a_summary" in summary
    assert "team_b_summary" in summary 