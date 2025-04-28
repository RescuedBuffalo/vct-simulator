#!/usr/bin/env python3
"""
View and analyze match statistics from a completed Valorant match simulation.
"""

import os
import json
import argparse
from tabulate import tabulate
from typing import Dict, List, Any

def load_match_stats(file_path: str) -> Dict:
    """Load match statistics from a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def print_match_summary(stats: Dict) -> None:
    """Print a summary of the match result."""
    winner = stats["winner"]
    score = stats["score"]
    map_name = stats["map"]
    duration = stats["duration"]
    rounds = stats["total_rounds"]
    overtime = stats.get("overtime_rounds", 0)
    
    print("\n" + "="*50)
    print(f"MATCH SUMMARY: {map_name}")
    print("="*50)
    print(f"Final Score: {score}")
    print(f"Winner: {winner.upper()}")
    print(f"Rounds Played: {rounds}" + (f" (including {overtime} overtime rounds)" if overtime else ""))
    print(f"Match Duration: {duration:.1f} seconds")
    print("="*50 + "\n")

def print_team_stats(stats: Dict) -> None:
    """Print team statistics."""
    team_a = stats["team_a_summary"]
    team_b = stats["team_b_summary"]
    
    print("\n" + "="*50)
    print("TEAM PERFORMANCE")
    print("="*50)
    
    # Create a table for team comparison
    headers = ["Statistic", "Team A", "Team B"]
    table_data = [
        ["Score", team_a["score"], team_b["score"]],
        ["Win Rate", f"{team_a['win_rate']}%", f"{team_b['win_rate']}%"],
        ["Attack Win Rate", f"{team_a['side_win_rates']['attack']}%", f"{team_b['side_win_rates']['attack']}%"],
        ["Defense Win Rate", f"{team_a['side_win_rates']['defense']}%", f"{team_b['side_win_rates']['defense']}%"],
        ["First Bloods", team_a["first_bloods"], team_b["first_bloods"]],
        ["Clutches", team_a["clutches"], team_b["clutches"]],
        ["Avg Damage/Round", team_a["avg_damage_per_round"], team_b["avg_damage_per_round"]],
        ["HS Percentage", f"{team_a['headshot_percentage']}%", f"{team_b['headshot_percentage']}%"],
        ["Flawless Rounds", team_a["flawless_rounds"], team_b["flawless_rounds"]],
        ["Thrifty Rounds", team_a["thrifty_rounds"], team_b["thrifty_rounds"]],
        ["Trade Efficiency", team_a["trade_efficiency"], team_b["trade_efficiency"]]
    ]
    
    print(tabulate(table_data, headers=headers, tablefmt="pretty"))
    
    # Print multi-kills
    print("\nMulti-Kills:")
    multi_kills_a = team_a.get("multi_kills", {})
    multi_kills_b = team_b.get("multi_kills", {})
    
    multi_headers = ["Multi-Kill", "Team A", "Team B"]
    multi_data = [
        ["2K", multi_kills_a.get("2k", 0), multi_kills_b.get("2k", 0)],
        ["3K", multi_kills_a.get("3k", 0), multi_kills_b.get("3k", 0)],
        ["4K", multi_kills_a.get("4k", 0), multi_kills_b.get("4k", 0)],
        ["5K", multi_kills_a.get("5k", 0), multi_kills_b.get("5k", 0)]
    ]
    
    print(tabulate(multi_data, headers=multi_headers, tablefmt="pretty"))
    
    # Print economy performance
    print("\nEconomy Performance:")
    eco_a = team_a.get("eco_performance", {})
    eco_b = team_b.get("eco_performance", {})
    
    eco_headers = ["Round Type", "Team A Win Rate", "Team B Win Rate"]
    eco_data = [
        ["Eco", f"{eco_a.get('eco', 0)}%", f"{eco_b.get('eco', 0)}%"],
        ["Bonus", f"{eco_a.get('bonus', 0)}%", f"{eco_b.get('bonus', 0)}%"],
        ["Full Buy", f"{eco_a.get('full_buy', 0)}%", f"{eco_b.get('full_buy', 0)}%"]
    ]
    
    print(tabulate(eco_data, headers=eco_headers, tablefmt="pretty"))
    
    # Print site preferences
    print("\nSite Preferences (Attack):")
    sites_a = team_a.get("site_preferences", {})
    sites_b = team_b.get("site_preferences", {})
    
    # Only print if data is available
    if sites_a or sites_b:
        site_headers = ["Site", "Team A Preference", "Team B Preference"]
        site_data = []
        
        all_sites = set(list(sites_a.keys()) + list(sites_b.keys()))
        for site in all_sites:
            site_data.append([
                site,
                f"{sites_a.get(site, 0)}%",
                f"{sites_b.get(site, 0)}%"
            ])
        
        print(tabulate(site_data, headers=site_headers, tablefmt="pretty"))
    
    print("="*50 + "\n")

def print_player_stats(stats: Dict) -> None:
    """Print individual player statistics."""
    player_stats = stats["player_stats"]
    
    print("\n" + "="*80)
    print("PLAYER PERFORMANCE")
    print("="*80)
    
    # Filter players into team A and team B
    # This is a simplification; in a real implementation you'd know which players are on which team
    team_a_players = list(player_stats.keys())[:5]  # First 5 players assumed to be team A
    team_b_players = list(player_stats.keys())[5:]  # Remaining players assumed to be team B
    
    for team_name, team_players in [("Team A", team_a_players), ("Team B", team_b_players)]:
        print(f"\n{team_name} Players:")
        
        # Create basic stats table
        headers = ["Player", "KDA", "ACS", "ADR", "HS%", "FB", "Clutches", "Util Dmg"]
        table_data = []
        
        for player_id in team_players:
            player = player_stats[player_id]
            table_data.append([
                player_id,
                player["kda"],
                player["acs"],
                player["adr"],
                f"{player['hs_percentage']}%",
                player["first_bloods"],
                player["clutches"],
                player["utility_damage"]
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="pretty"))
    
    # Print top performers
    print("\nTop Performers:")
    
    # Sort players by ACS
    top_acs = sorted([(pid, player_stats[pid]["acs"]) for pid in player_stats], 
                    key=lambda x: x[1], reverse=True)[:3]
    
    # Sort players by kills (parsing KDA string)
    top_kills = sorted([(pid, int(player_stats[pid]["kda"].split('/')[0])) for pid in player_stats], 
                      key=lambda x: x[1], reverse=True)[:3]
    
    # Sort players by first bloods
    top_fb = sorted([(pid, player_stats[pid]["first_bloods"]) for pid in player_stats], 
                   key=lambda x: x[1], reverse=True)[:3]
    
    # Sort players by headshot percentage
    top_hs = sorted([(pid, player_stats[pid]["hs_percentage"]) for pid in player_stats], 
                   key=lambda x: x[1], reverse=True)[:3]
    
    performance_headers = ["Category", "1st", "2nd", "3rd"]
    performance_data = [
        ["ACS", f"{top_acs[0][0]} ({top_acs[0][1]})", 
               f"{top_acs[1][0]} ({top_acs[1][1]})", 
               f"{top_acs[2][0]} ({top_acs[2][1]})"],
        ["Kills", f"{top_kills[0][0]} ({top_kills[0][1]})", 
                 f"{top_kills[1][0]} ({top_kills[1][1]})", 
                 f"{top_kills[2][0]} ({top_kills[2][1]})"],
        ["First Bloods", f"{top_fb[0][0]} ({top_fb[0][1]})", 
                        f"{top_fb[1][0]} ({top_fb[1][1]})", 
                        f"{top_fb[2][0]} ({top_fb[2][1]})"],
        ["HS%", f"{top_hs[0][0]} ({top_hs[0][1]}%)", 
               f"{top_hs[1][0]} ({top_hs[1][1]}%)", 
               f"{top_hs[2][0]} ({top_hs[2][1]}%)"]
    ]
    
    print(tabulate(performance_data, headers=performance_headers, tablefmt="pretty"))
    print("="*80 + "\n")

def print_round_analysis(stats: Dict) -> None:
    """Print round-by-round analysis."""
    round_results = stats.get("round_results", [])
    
    if not round_results:
        return
    
    print("\n" + "="*60)
    print("ROUND ANALYSIS")
    print("="*60)
    
    # Group rounds by phases (e.g., first half, second half, overtime)
    first_half = [r for r in round_results if r["round"] <= 12]
    second_half = [r for r in round_results if 12 < r["round"] <= 24]
    overtime = [r for r in round_results if r["round"] > 24]
    
    # Print summary for each half
    halves = [
        ("First Half", first_half),
        ("Second Half", second_half)
    ]
    
    if overtime:
        halves.append(("Overtime", overtime))
    
    for half_name, rounds in halves:
        if not rounds:
            continue
            
        print(f"\n{half_name}:")
        
        team_a_wins = sum(1 for r in rounds if r["winner"] == "team_a")
        team_b_wins = len(rounds) - team_a_wins
        
        print(f"Team A: {team_a_wins} rounds, Team B: {team_b_wins} rounds")
        
        # Analyze round end conditions
        end_conditions = {}
        for r in rounds:
            condition = r.get("end_condition", "unknown")
            if condition not in end_conditions:
                end_conditions[condition] = 0
            end_conditions[condition] += 1
        
        print("\nRound End Conditions:")
        for condition, count in end_conditions.items():
            print(f"  {condition}: {count} rounds ({(count/len(rounds))*100:.1f}%)")
    
    print("="*60 + "\n")

def print_mvp(stats: Dict) -> None:
    """Print MVP information."""
    mvp = stats.get("mvp", {})
    
    if not mvp:
        return
    
    mvp_id = mvp.get("id", "Unknown")
    mvp_acs = mvp.get("acs", 0)
    mvp_kda = mvp.get("kda", "0/0/0")
    
    print("\n" + "="*50)
    print("MATCH MVP")
    print("="*50)
    print(f"Player: {mvp_id}")
    print(f"ACS: {mvp_acs}")
    print(f"KDA: {mvp_kda}")
    print("="*50 + "\n")

def export_match_stats(stats: Dict, output_file: str) -> None:
    """Export match statistics to various formats."""
    # For simplicity, just export as JSON
    with open(output_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"Match statistics exported to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="View and analyze match statistics")
    parser.add_argument("stats_file", help="Path to match statistics JSON file")
    parser.add_argument("--export", help="Export statistics to file", default=None)
    parser.add_argument("--summary", action="store_true", help="Show only match summary")
    
    args = parser.parse_args()
    
    try:
        stats = load_match_stats(args.stats_file)
        
        print_match_summary(stats)
        
        if not args.summary:
            print_team_stats(stats)
            print_player_stats(stats)
            print_round_analysis(stats)
            print_mvp(stats)
        
        if args.export:
            export_match_stats(stats, args.export)
            
    except FileNotFoundError:
        print(f"Error: File {args.stats_file} not found")
    except json.JSONDecodeError:
        print(f"Error: File {args.stats_file} is not valid JSON")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 