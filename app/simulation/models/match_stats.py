from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
import statistics
from .player_stats import PlayerMatchStats
from .team_stats import EnhancedTeamStats
from datetime import datetime, timedelta
import os


@dataclass
class MatchStats:
    """Comprehensive statistics for an entire match."""
    # Team Stats
    team_a_stats: EnhancedTeamStats = field(default_factory=EnhancedTeamStats)
    team_b_stats: EnhancedTeamStats = field(default_factory=EnhancedTeamStats)
    
    # Player Stats (by player ID)
    player_stats: Dict[str, PlayerMatchStats] = field(default_factory=dict)
    
    # Match Events
    round_results: List[Dict[str, Any]] = field(default_factory=list)
    kill_events: List[Dict[str, Any]] = field(default_factory=list)
    plant_events: List[Dict[str, Any]] = field(default_factory=list)
    defuse_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timeline tracking
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    
    # Match metadata
    total_rounds: int = 0
    overtime_rounds: int = 0
    map_name: str = ""
    match_duration: float = 0.0
    
    # New match stats
    match_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    
    # Team names
    team1_name: str = ""
    team2_name: str = ""
    
    # Match outcome
    winner: Optional[str] = None
    final_score: Dict[str, int] = field(default_factory=dict)
    is_overtime: bool = False
    
    # Round history
    round_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Match flow statistics
    longest_win_streak: Dict[str, Any] = field(default_factory=dict)
    lead_changes: int = 0
    ties: int = 0
    current_streak: Dict[str, Any] = field(default_factory=dict)
    max_lead: Dict[str, Any] = field(default_factory=dict)
    
    # Economy stats
    eco_wins: Dict[str, int] = field(default_factory=dict)
    force_buy_wins: Dict[str, int] = field(default_factory=dict)
    
    # Clutch situations (1vX)
    clutches: Dict[str, Dict[str, Dict[str, int]]] = field(default_factory=dict)
    
    # Side stats
    side_wins: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Comeback metrics
    biggest_comeback: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the match stats."""
        self.total_rounds = 0
    
    def initialize_player(self, player_id: str) -> PlayerMatchStats:
        """Initialize stats for a player."""
        if player_id not in self.player_stats:
            self.player_stats[player_id] = PlayerMatchStats()
        return self.player_stats[player_id]
    
    def record_kill(self, round_number: int, time: float, killer_id: str, victim_id: str,
                   weapon: str, is_headshot: bool, position: Tuple[float, float],
                   is_wallbang: bool = False, assist_ids: List[str] = None,
                   is_first_blood: bool = False, is_trade: bool = False,
                   is_through_smoke: bool = False, flash_assist_id: Optional[str] = None,
                   killer_health: int = 100, killer_team: str = "", victim_team: str = ""):
        """Record a kill event with detailed metadata."""
        # Update kill event record
        kill_event = {
            "round": round_number,
            "time": time,
            "killer_id": killer_id,
            "victim_id": victim_id,
            "weapon": weapon,
            "is_headshot": is_headshot,
            "position": position,
            "is_wallbang": is_wallbang,
            "assist_ids": assist_ids or [],
            "is_first_blood": is_first_blood,
            "is_trade": is_trade,
            "is_through_smoke": is_through_smoke,
            "flash_assist_id": flash_assist_id,
            "killer_health": killer_health,
            "killer_team": killer_team,
            "victim_team": victim_team
        }
        self.kill_events.append(kill_event)
        
        # Add to timeline
        self.timeline.append({
            "type": "kill",
            "round": round_number,
            "time": time,
            "data": kill_event
        })
        
        # Update killer stats
        if killer_id in self.player_stats:
            # Count multi-kills in the current round
            multi_kill_count = sum(1 for event in self.kill_events 
                                if event["round"] == round_number and 
                                event["killer_id"] == killer_id)
            
            # Eco/bonus detection
            is_eco_kill = False
            if round_number > 1:
                # Simple approach: if victim's team had much lower equipment value
                # Could be refined with actual equipment value tracking
                is_eco_kill = True
            
            self.player_stats[killer_id].record_kill(
                weapon=weapon,
                is_headshot=is_headshot,
                position=position,
                is_first_blood=is_first_blood,
                is_wallbang=is_wallbang,
                multi_kill_count=multi_kill_count,
                is_trade=is_trade,
                is_entry=(is_first_blood and multi_kill_count == 1),
                is_clutch=self._is_clutch_situation(round_number, killer_team),
                is_eco_kill=is_eco_kill
            )
        
        # Update victim stats
        if victim_id in self.player_stats:
            is_traded = self._will_be_traded(round_number, time, victim_id, victim_team)
            self.player_stats[victim_id].record_death(
                position=position,
                killer_weapon=weapon,
                is_first_death=is_first_blood,
                is_traded=is_traded,
                is_entry_death=(is_first_blood and victim_team != killer_team),
                during_eco=False  # Would need economy tracking
            )
        
        # Update assist stats
        if assist_ids:
            for assist_id in assist_ids:
                if assist_id in self.player_stats:
                    self.player_stats[assist_id].assists += 1
        
        # Update flash assist stats
        if flash_assist_id and flash_assist_id in self.player_stats and flash_assist_id != killer_id:
            self.player_stats[flash_assist_id].assists += 1
            
        # Update team stats for first bloods
        if is_first_blood:
            if killer_team == "team_a":
                self.team_a_stats.first_bloods += 1
                self.team_b_stats.first_deaths += 1
            else:
                self.team_b_stats.first_bloods += 1
                self.team_a_stats.first_deaths += 1
                
        # Update team stats for trades
        if is_trade:
            if killer_team == "team_a":
                self.team_a_stats.record_trade(is_for=True)
                self.team_b_stats.record_trade(is_for=False)
            else:
                self.team_b_stats.record_trade(is_for=True)
                self.team_a_stats.record_trade(is_for=False)
    
    def record_damage(self, round_number: int, time: float, attacker_id: str,
                    victim_id: str, damage: int, weapon: str, hitbox: str,
                    attacker_position: Tuple[float, float], victim_position: Tuple[float, float],
                    is_through_smoke: bool = False, is_wallbang: bool = False,
                    is_utility: bool = False):
        """Record a damage event."""
        # Update timeline
        damage_event = {
            "round": round_number,
            "time": time,
            "attacker_id": attacker_id,
            "victim_id": victim_id,
            "damage": damage,
            "weapon": weapon,
            "hitbox": hitbox,
            "attacker_position": attacker_position,
            "victim_position": victim_position,
            "is_through_smoke": is_through_smoke,
            "is_wallbang": is_wallbang,
            "is_utility": is_utility
        }
        
        self.timeline.append({
            "type": "damage",
            "round": round_number,
            "time": time,
            "data": damage_event
        })
        
        # Update player stats
        if attacker_id in self.player_stats:
            is_headshot = hitbox == "head"
            is_bodyshot = hitbox == "body"
            is_legshot = hitbox == "legs"
            
            self.player_stats[attacker_id].record_damage(
                damage=damage,
                weapon=weapon,
                is_headshot=is_headshot,
                is_bodyshot=is_bodyshot,
                is_legshot=is_legshot,
                is_utility=is_utility
            )
        
        if victim_id in self.player_stats:
            self.player_stats[victim_id].damage_received += damage
    
    def record_plant(self, round_number: int, time: float, planter_id: str,
                    site: str, position: Tuple[float, float], team: str,
                    remaining_defenders: int, time_elapsed: float):
        """Record a spike plant event."""
        # Record event
        plant_event = {
            "round": round_number,
            "time": time,
            "planter_id": planter_id,
            "site": site,
            "position": position,
            "team": team,
            "remaining_defenders": remaining_defenders,
            "time_elapsed": time_elapsed
        }
        self.plant_events.append(plant_event)
        
        # Add to timeline
        self.timeline.append({
            "type": "plant",
            "round": round_number,
            "time": time,
            "data": plant_event
        })
        
        # Update player stats
        if planter_id in self.player_stats:
            self.player_stats[planter_id].record_plant(site)
        
        # Update team stats
        if team == "team_a":
            self.team_a_stats.record_plant(site, time_elapsed)
        else:
            self.team_b_stats.record_plant(site, time_elapsed)
    
    def record_defuse(self, round_number: int, time: float, defuser_id: str,
                     site: str, position: Tuple[float, float], team: str,
                     remaining_attackers: int, was_retake: bool = False):
        """Record a spike defuse event."""
        # Record event
        defuse_event = {
            "round": round_number,
            "time": time,
            "defuser_id": defuser_id,
            "site": site,
            "position": position,
            "team": team,
            "remaining_attackers": remaining_attackers,
            "was_retake": was_retake
        }
        self.defuse_events.append(defuse_event)
        
        # Add to timeline
        self.timeline.append({
            "type": "defuse",
            "round": round_number,
            "time": time,
            "data": defuse_event
        })
        
        # Update player stats
        if defuser_id in self.player_stats:
            self.player_stats[defuser_id].record_defuse()
        
        # Update team stats
        if team == "team_a":
            self.team_a_stats.record_defuse(site, was_retake)
        else:
            self.team_b_stats.record_defuse(site, was_retake)
    
    def record_utility_usage(self, round_number: int, time: float, player_id: str,
                           utility_type: str, position: Tuple[float, float],
                           enemies_affected: int = 0, teammates_affected: int = 0,
                           blind_duration: float = 0.0, damage_dealt: int = 0):
        """Record utility usage."""
        # Update timeline
        utility_event = {
            "round": round_number,
            "time": time,
            "player_id": player_id,
            "utility_type": utility_type,
            "position": position,
            "enemies_affected": enemies_affected,
            "teammates_affected": teammates_affected,
            "blind_duration": blind_duration,
            "damage_dealt": damage_dealt
        }
        
        self.timeline.append({
            "type": "utility",
            "round": round_number,
            "time": time,
            "data": utility_event
        })
        
        # Update player stats
        if player_id in self.player_stats:
            self.player_stats[player_id].record_utility_usage(
                utility_type=utility_type,
                enemies_affected=enemies_affected,
                teammates_affected=teammates_affected,
                blind_duration=blind_duration
            )
    
    def record_round_result(self, round_number: int, winner: str, end_condition: str,
                          site: Optional[str], time_remaining: float,
                          team_a_alive: int, team_b_alive: int,
                          team_a_equipment: int, team_b_equipment: int,
                          team_a_side: str, team_b_side: str,
                          is_overtime: bool = False):
        """Record the result of a round."""
        self.total_rounds += 1
        if is_overtime:
            self.overtime_rounds += 1
            
        # Record round result
        round_result = {
            "round": round_number,
            "winner": winner,
            "end_condition": end_condition,
            "site": site,
            "time_remaining": time_remaining,
            "team_a_alive": team_a_alive,
            "team_b_alive": team_b_alive,
            "team_a_equipment": team_a_equipment,
            "team_b_equipment": team_b_equipment,
            "team_a_side": team_a_side,
            "team_b_side": team_b_side,
            "is_overtime": is_overtime
        }
        self.round_results.append(round_result)
        
        # Add to timeline
        self.timeline.append({
            "type": "round_end",
            "round": round_number,
            "time": 0.0,  # End of round
            "data": round_result
        })
        
        # Update team stats
        score_difference_a = (self.team_a_stats.rounds_won - self.team_b_stats.rounds_won)
        score_difference_b = (self.team_b_stats.rounds_won - self.team_a_stats.rounds_won)
        
        # Determine economy round types
        team_a_round_type = self._determine_economy_round_type(team_a_equipment)
        team_b_round_type = self._determine_economy_round_type(team_b_equipment)
        
        # Update team A stats
        self.team_a_stats.record_round_result(
            round_number=round_number,
            won=(winner == "team_a"),
            side=team_a_side,
            equipment_value=team_a_equipment,
            enemies_alive=team_b_alive,
            time_remaining=time_remaining,
            score_difference=score_difference_a,
            end_condition=end_condition,
            site=site
        )
        self.team_a_stats.record_economy_round(team_a_round_type, winner == "team_a")
        
        # Update team B stats
        self.team_b_stats.record_round_result(
            round_number=round_number,
            won=(winner == "team_b"),
            side=team_b_side,
            equipment_value=team_b_equipment,
            enemies_alive=team_a_alive,
            time_remaining=time_remaining,
            score_difference=score_difference_b,
            end_condition=end_condition,
            site=site
        )
        self.team_b_stats.record_economy_round(team_b_round_type, winner == "team_b")
        
        # Update player round stats
        for player_id, stats in self.player_stats.items():
            # Get player stats for this round
            round_kills = sum(1 for event in self.kill_events 
                            if event["round"] == round_number and
                            event["killer_id"] == player_id)
            
            round_deaths = sum(1 for event in self.kill_events 
                             if event["round"] == round_number and
                             event["victim_id"] == player_id)
            
            # Calculate damage for this round
            round_damage = 0
            for event in self.timeline:
                if (event["type"] == "damage" and 
                    event["round"] == round_number and
                    event["data"]["attacker_id"] == player_id):
                    round_damage += event["data"]["damage"]
            
            # Determine which team the player is on and if they won
            player_team = None
            for event in self.kill_events:
                if event["killer_id"] == player_id:
                    player_team = event["killer_team"]
                    break
                elif event["victim_id"] == player_id:
                    player_team = event["victim_team"]
                    break
            
            if player_team:
                player_won = (player_team == winner)
                player_side = team_a_side if player_team == "team_a" else team_b_side
                # Estimate credits earned
                credits_earned = 3000 if player_won else 1900
                credits_earned += round_kills * 200
                
                stats.record_round_stats(
                    round_number=round_number,
                    kills=round_kills,
                    deaths=round_deaths,
                    damage=round_damage,
                    credits_earned=credits_earned,
                    side=player_side,
                    won_round=player_won
                )
    
    def record_purchase(self, round_number: int, time: float, player_id: str,
                      item_type: str, cost: int):
        """Record a purchase."""
        # Update timeline
        purchase_event = {
            "round": round_number,
            "time": time,
            "player_id": player_id,
            "item_type": item_type,
            "cost": cost
        }
        
        self.timeline.append({
            "type": "purchase",
            "round": round_number,
            "time": time,
            "data": purchase_event
        })
        
        # Update player stats
        if player_id in self.player_stats:
            self.player_stats[player_id].record_purchase(item_type, cost)
    
    def record_clutch_situation(self, round_number: int, time: float,
                              player_id: str, team: str, enemies_remaining: int,
                              allies_remaining: int = 0, won: bool = False):
        """Record a clutch situation."""
        # Update timeline
        clutch_event = {
            "round": round_number,
            "time": time,
            "player_id": player_id,
            "team": team,
            "enemies_remaining": enemies_remaining,
            "allies_remaining": allies_remaining,
            "won": won
        }
        
        self.timeline.append({
            "type": "clutch",
            "round": round_number,
            "time": time,
            "data": clutch_event
        })
        
        # Update player stats
        if player_id in self.player_stats:
            self.player_stats[player_id].attempt_clutch(won, enemies_remaining)
            
        # Update team stats
        if won:
            if team == "team_a":
                self.team_a_stats.clutches += 1
            else:
                self.team_b_stats.clutches += 1
        
        if team == "team_a":
            self.team_a_stats.clutches_attempted += 1
        else:
            self.team_b_stats.clutches_attempted += 1
    
    def record_entry_attempt(self, round_number: int, time: float,
                           player_id: str, team: str, position: Tuple[float, float],
                           success: bool, site: str):
        """Record an entry attempt."""
        # Update timeline
        entry_event = {
            "round": round_number,
            "time": time,
            "player_id": player_id,
            "team": team,
            "position": position,
            "success": success,
            "site": site
        }
        
        self.timeline.append({
            "type": "entry",
            "round": round_number,
            "time": time,
            "data": entry_event
        })
        
        # Update player stats
        if player_id in self.player_stats:
            self.player_stats[player_id].attempt_entry(success)
    
    def record_site_defense(self, round_number: int, time: float,
                          player_id: str, team: str, site: str, success: bool):
        """Record a site defense."""
        # Update timeline
        defense_event = {
            "round": round_number,
            "time": time,
            "player_id": player_id,
            "team": team,
            "site": site,
            "success": success
        }
        
        self.timeline.append({
            "type": "site_defense",
            "round": round_number,
            "time": time,
            "data": defense_event
        })
        
        # Update player stats
        if player_id in self.player_stats:
            self.player_stats[player_id].record_site_defense(site, success)
    
    def record_retake(self, round_number: int, time: float, site: str,
                    player_ids: List[str], team: str, success: bool):
        """Record a retake attempt."""
        # Update timeline
        retake_event = {
            "round": round_number,
            "time": time,
            "player_ids": player_ids,
            "team": team,
            "site": site,
            "success": success
        }
        
        self.timeline.append({
            "type": "retake",
            "round": round_number,
            "time": time,
            "data": retake_event
        })
        
        # Update player stats
        for player_id in player_ids:
            if player_id in self.player_stats:
                self.player_stats[player_id].record_retake(success)
    
    def record_match_end(self, winner: str, final_score_a: int, final_score_b: int,
                       match_duration: float, total_rounds: int):
        """Record the end of a match."""
        self.match_duration = match_duration
        self.total_rounds = total_rounds
        
        # Update calculated stats
        self.team_a_stats.update_from_player_stats(
            {pid: stats for pid, stats in self.player_stats.items() 
             if any(event["killer_team"] == "team_a" for event in self.kill_events 
                  if event["killer_id"] == pid)},
            total_rounds
        )
        
        self.team_b_stats.update_from_player_stats(
            {pid: stats for pid, stats in self.player_stats.items() 
             if any(event["killer_team"] == "team_b" for event in self.kill_events 
                  if event["killer_id"] == pid)},
            total_rounds
        )
        
        # Update all player ratios
        for stats in self.player_stats.values():
            stats.update_ratios()
    
    def get_mvp(self) -> Tuple[str, PlayerMatchStats]:
        """Get the MVP of the match based on ACS."""
        if not self.player_stats:
            return None, None
            
        # Update all player ratios first
        for pid, stats in self.player_stats.items():
            stats.update_ratios()
            
        # Find player with highest ACS
        mvp_id = max(self.player_stats.keys(), key=lambda pid: self.player_stats[pid].average_combat_score)
        return mvp_id, self.player_stats[mvp_id]
    
    def get_top_performers(self, category: str = "kills", count: int = 3) -> List[Tuple[str, Any]]:
        """Get top performers in a specific category."""
        if not self.player_stats:
            return []
            
        if category == "kills":
            return sorted([(pid, stats.kills) for pid, stats in self.player_stats.items()],
                         key=lambda x: x[1], reverse=True)[:count]
        elif category == "acs":
            for stats in self.player_stats.values():
                stats.update_ratios()
            return sorted([(pid, stats.average_combat_score) for pid, stats in self.player_stats.items()],
                         key=lambda x: x[1], reverse=True)[:count]
        elif category == "first_bloods":
            return sorted([(pid, stats.first_bloods) for pid, stats in self.player_stats.items()],
                         key=lambda x: x[1], reverse=True)[:count]
        elif category == "clutches":
            return sorted([(pid, stats.clutches) for pid, stats in self.player_stats.items()],
                         key=lambda x: x[1], reverse=True)[:count]
        elif category == "headshot_percentage":
            return sorted([(pid, stats.get_headshot_percentage()) for pid, stats in self.player_stats.items()],
                         key=lambda x: x[1], reverse=True)[:count]
        elif category == "utility_damage":
            return sorted([(pid, stats.damage_by_utility) for pid, stats in self.player_stats.items()],
                         key=lambda x: x[1], reverse=True)[:count]
        elif category == "damage":
            return sorted([(pid, stats.damage_dealt) for pid, stats in self.player_stats.items()],
                         key=lambda x: x[1], reverse=True)[:count]
        else:
            return []
    
    def get_match_summary(self, write_to_file: bool = False) -> Dict:
        """Get a comprehensive summary of the match."""
        mvp_id, mvp_stats = self.get_mvp()
        

        summary = {
            "score": f"{self.team_a_stats.rounds_won}-{self.team_b_stats.rounds_won}",
            "winner": "team_a" if self.team_a_stats.rounds_won > self.team_b_stats.rounds_won else "team_b",
            "duration": self.match_duration,
            "total_rounds": self.total_rounds,
            "overtime_rounds": self.overtime_rounds,
            "map": self.map_name,
            "mvp": {
                "id": mvp_id,
                "acs": round(mvp_stats.average_combat_score, 1) if mvp_stats else 0,
                "kda": f"{mvp_stats.kills}/{mvp_stats.deaths}/{mvp_stats.assists}" if mvp_stats else "0/0/0"
            },
            "top_killers": [(pid, kills) for pid, kills in self.get_top_performers(category="kills", count=3)],
            "team_a_summary": self.team_a_stats.get_summary(),
            "team_b_summary": self.team_b_stats.get_summary(),
            "player_stats": {pid: stats.get_summary() for pid, stats in self.player_stats.items()}
        }

        if write_to_file:
            import json
            summaries_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "summaries")
            os.makedirs(summaries_dir, exist_ok=True)
            with open(os.path.join(summaries_dir, f"match_stats_{self.map_name}.json"), "w") as f:
                json.dump(summary, f)

        return summary
    
    def _is_clutch_situation(self, round_number: int, team: str) -> bool:
        """Check if a player is in a clutch situation."""
        # A simple implementation assuming a clutch is a 1vX situation
        # Would need more detailed tracking for proper implementation
        return False  # Placeholder
    
    def _will_be_traded(self, round_number: int, time: float, victim_id: str, victim_team: str) -> bool:
        """Check if a player will be traded within the trade window."""
        # Check for a trade within 3 seconds
        TRADE_WINDOW = 3.0
        
        for event in self.kill_events:
            if (event["round"] == round_number and
                event["time"] > time and
                event["time"] <= time + TRADE_WINDOW and
                event["victim_team"] != victim_team):
                return True
        return False
    
    def _determine_economy_round_type(self, equipment_value: int) -> str:
        """Determine if a round is an eco, bonus, or full-buy based on equipment value."""
        if equipment_value < 6000:
            return "eco"
        elif equipment_value < 12000:
            return "bonus"
        else:
            return "full_buy"
    
    def record_round_end(self, round_number: int, winner: str, loser: str, 
                        winner_side: str, round_time: float, 
                        winning_condition: str, site: Optional[str] = None,
                        eco_status: Dict[str, str] = None) -> None:
        """
        Record the end of a round.
        
        Parameters:
            round_number: Current round number
            winner: Name of winning team ('team1' or 'team2')
            loser: Name of losing team ('team1' or 'team2')
            winner_side: Side of winning team ('attack' or 'defense')
            round_time: Time taken for round in seconds
            winning_condition: How round was won ('elimination', 'spike_planted', 'spike_defused', 'time_expired')
            site: Site where action happened, if applicable
            eco_status: Dict with team eco status {'team1': 'full_buy', 'team2': 'eco', etc.}
        """
        # Update scores and round count
        self.total_rounds += 1
        self.final_score[winner] += 1
        
        # Get team names for clarity
        winner_name = self.team1_name if winner == "team1" else self.team2_name
        loser_name = self.team1_name if loser == "team1" else self.team2_name
        
        # Update side wins
        self.side_wins[winner][winner_side] += 1
        
        # Calculate score differential
        team1_score = self.final_score["team1"]
        team2_score = self.final_score["team2"]
        differential = abs(team1_score - team2_score)
        
        # Check for new max lead
        leading_team = "team1" if team1_score > team2_score else "team2" if team2_score > team1_score else ""
        if leading_team and differential > self.max_lead["lead"]:
            self.max_lead = {"team": leading_team, "lead": differential}
        
        # Check for tie
        if team1_score == team2_score:
            self.ties += 1
        
        # Check for lead change
        if self.round_history:
            prev_team1_score = self.round_history[-1]["score"]["team1"]
            prev_team2_score = self.round_history[-1]["score"]["team2"]
            prev_leader = "team1" if prev_team1_score > prev_team2_score else "team2" if prev_team2_score > prev_team1_score else ""
            
            if prev_leader and leading_team and prev_leader != leading_team:
                self.lead_changes += 1
        
        # Update winning streak
        if not self.current_streak["team"] or self.current_streak["team"] == winner:
            # Continue streak
            if not self.current_streak["team"]:
                self.current_streak["team"] = winner
            self.current_streak["streak"] += 1
            
            # Check if this is a new longest streak
            if self.current_streak["streak"] > self.longest_win_streak["streak"]:
                self.longest_win_streak = self.current_streak.copy()
        else:
            # Streak broken, check for comeback
            prev_streak = self.current_streak["streak"]
            if prev_streak >= 3:  # Minimum streak to consider for comeback
                # The team that just won broke a streak of 3+ by the other team
                self.biggest_comeback = max(
                    self.biggest_comeback,
                    {"team": winner, "deficit": prev_streak},
                    key=lambda x: x.get("deficit", 0)
                )
            
            # Reset streak for new winner
            self.current_streak = {"team": winner, "streak": 1}
        
        # Record eco stats if provided
        if eco_status:
            winner_eco = eco_status.get(winner)
            loser_eco = eco_status.get(loser)
            
            if winner_eco == "eco" and loser_eco in ["full_buy", "half_buy"]:
                self.eco_wins[winner] += 1
            elif winner_eco == "force_buy":
                self.force_buy_wins[winner] += 1
        
        # Create round summary
        round_summary = {
            "round_number": round_number,
            "winner": winner,
            "winner_name": winner_name,
            "loser": loser,
            "loser_name": loser_name,
            "winner_side": winner_side,
            "round_time": round_time,
            "winning_condition": winning_condition,
            "site": site,
            "score": self.final_score.copy(),
            "eco_status": eco_status,
        }
        
        # Add to round history
        self.round_history.append(round_summary)
    
    def finalize_match(self, winner: str) -> None:
        """Finalize match stats after completion."""
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.winner = winner
        
        # Check if match went to overtime
        self.is_overtime = self.total_rounds > 24  # Standard match is max 24 rounds
    
    def get_summary(self, write_to_file: bool = False) -> Dict[str, Any]:
        """Get a summary of match stats."""
        team1_stats_summary = self.team_a_stats.get_summary() if hasattr(self.team_a_stats, 'get_summary') else {}
        team2_stats_summary = self.team_b_stats.get_summary() if hasattr(self.team_b_stats, 'get_summary') else {}

        if write_to_file:
            import json
            import os
            summaries_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "summaries")
            os.makedirs(summaries_dir, exist_ok=True)
            with open(os.path.join(summaries_dir, f"match_stats_{self.map_name}.json"), "w") as f:
                json.dump(self.get_summary(write_to_file=True), f)

        return {
            "map": self.map_name,
            "duration": str(timedelta(seconds=int(self.duration))) if self.duration else None,
            "winner": self.winner,
            "final_score": self.final_score,
            "total_rounds": self.total_rounds,
            "is_overtime": self.is_overtime,
            "team_stats": {
                self.team1_name: team1_stats_summary,
                self.team2_name: team2_stats_summary
            },
            "match_flow": {
                "longest_win_streak": self.longest_win_streak,
                "lead_changes": self.lead_changes,
                "ties": self.ties,
                "max_lead": self.max_lead,
                "biggest_comeback": self.biggest_comeback
            },
            "side_wins": self.side_wins,
            "eco_wins": self.eco_wins,
            "force_buy_wins": self.force_buy_wins,
            "clutches": self.clutches
        }
    
    def get_player_performances(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get detailed player performances from team stats."""
        result = {}
        
        # Logic to extract and aggregate player stats from both teams
        # This assumes team stats tracks individual player performances
        
        return result 