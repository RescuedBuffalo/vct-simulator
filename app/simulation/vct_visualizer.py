#!/usr/bin/env python3
import sys
import os
import math
import pygame
from typing import List, Dict, Tuple, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.simulation.vct_simulator import Team, Match, Tournament

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
CYAN = (0, 255, 255)

# Tournament visualization constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 30
TEAM_BOX_WIDTH = 200
TEAM_BOX_HEIGHT = 40
BRACKET_PADDING = 50
MATCH_SPACING = 20
GROUP_SPACING = 150

class VCTVisualizer:
    """Visualizes VCT tournament data."""
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.screen = None
        self.font = None
        self.title_font = None
        self.running = False
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(f"VCT Simulator - {tournament.name}")
        
        # Initialize fonts
        self.font = pygame.font.SysFont(None, 24)
        self.title_font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 18)
        
        # Clock for controlling frame rate
        self.clock = pygame.time.Clock()
    
    def run(self):
        """Run the visualization loop."""
        self.running = True
        
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
            
            # Draw everything
            self.screen.fill(WHITE)
            self.draw_tournament()
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()
    
    def draw_tournament(self):
        """Draw the tournament visualization."""
        # Draw tournament title
        title_text = self.title_font.render(self.tournament.name, True, BLACK)
        title_rect = title_text.get_rect(centerx=SCREEN_WIDTH//2, y=20)
        self.screen.blit(title_text, title_rect)
        
        # Organize matches by stage (group stage and playoffs)
        group_matches = []
        playoff_matches = []
        
        for match in self.tournament.matches:
            if match.format_type == "Bo1":
                group_matches.append(match)
            else:
                playoff_matches.append(match)
        
        # Draw group stage
        if group_matches:
            self.draw_group_stage(group_matches)
        
        # Draw playoffs
        if playoff_matches:
            self.draw_playoffs(playoff_matches)
        
        # Draw standings
        self.draw_standings()
    
    def draw_group_stage(self, matches: List[Match]):
        """Draw the group stage matches."""
        # Draw section title
        title_text = self.title_font.render("Group Stage", True, BLACK)
        title_rect = title_text.get_rect(x=50, y=80)
        self.screen.blit(title_text, title_rect)
        
        # Group teams to identify groups
        teams_by_group: Dict[str, List[Team]] = {}
        
        # Simplified grouping - just use first matches to determine groups
        for match in matches:
            # Create a unique group ID based on the teams in the first few matches
            for team in [match.team1, match.team2]:
                found = False
                for group_id, group_teams in teams_by_group.items():
                    if team in group_teams:
                        found = True
                        break
                
                if not found:
                    # Try to find a group with shared opponents
                    for group_id, group_teams in teams_by_group.items():
                        for existing_team in group_teams:
                            # Check if this team plays against any team in existing groups
                            for m in matches:
                                if ((m.team1 == team and m.team2 == existing_team) or
                                    (m.team2 == team and m.team1 == existing_team)):
                                    teams_by_group[group_id].append(team)
                                    found = True
                                    break
                            if found:
                                break
                        if found:
                            break
                    
                    if not found:
                        # Create a new group
                        new_group_id = f"Group {len(teams_by_group) + 1}"
                        teams_by_group[new_group_id] = [team]
        
        # Now draw each group
        group_y = 120
        for group_id, teams in teams_by_group.items():
            # Draw group header
            group_text = self.font.render(group_id, True, BLACK)
            self.screen.blit(group_text, (50, group_y))
            
            # Draw teams in this group
            team_y = group_y + 30
            for team in teams:
                team_text = self.font.render(f"{team.name} ({team.region})", True, BLACK)
                wins_text = self.font.render(f"W: {team.wins} L: {team.losses}", True, BLACK)
                
                self.screen.blit(team_text, (70, team_y))
                self.screen.blit(wins_text, (300, team_y))
                team_y += 25
            
            # Draw matches for this group
            match_y = team_y + 10
            group_matches = [m for m in matches if m.team1 in teams or m.team2 in teams]
            for match in group_matches:
                # Draw match details
                match_text = self.small_font.render(
                    f"{match.team1.name} vs {match.team2.name} - {match.map_name}", 
                    True, BLACK
                )
                self.screen.blit(match_text, (70, match_y))
                
                # Draw match result if available
                if match.winner:
                    result_text = self.small_font.render(
                        f"{match.team1_score} - {match.team2_score} (Winner: {match.winner.name})",
                        True, BLUE
                    )
                    self.screen.blit(result_text, (350, match_y))
                
                match_y += 20
            
            group_y = match_y + GROUP_SPACING
    
    def draw_playoffs(self, matches: List[Match]):
        """Draw the playoff bracket."""
        # Draw section title
        title_text = self.title_font.render("Playoffs", True, BLACK)
        title_rect = title_text.get_rect(x=SCREEN_WIDTH//2, y=80)
        self.screen.blit(title_text, title_rect)
        
        # Sort matches by round (semifinals, finals)
        # For this simplified version, just draw matches in the order they appear
        start_x = SCREEN_WIDTH//2 - (len(matches) * (TEAM_BOX_WIDTH + MATCH_SPACING))//2
        start_y = 130
        
        for i, match in enumerate(matches):
            match_x = start_x + i * (TEAM_BOX_WIDTH + MATCH_SPACING)
            
            # Draw team boxes
            self.draw_team_box(match.team1, match_x, start_y, match.team1_score)
            self.draw_team_box(match.team2, match_x, start_y + TEAM_BOX_HEIGHT + 10, match.team2_score)
            
            # Draw map name
            map_text = self.small_font.render(match.map_name, True, BLACK)
            map_rect = map_text.get_rect(centerx=match_x + TEAM_BOX_WIDTH//2, y=start_y + 2*TEAM_BOX_HEIGHT + 15)
            self.screen.blit(map_text, map_rect)
            
            # Draw winner indicator
            if match.winner:
                winner_y = start_y if match.winner == match.team1 else start_y + TEAM_BOX_HEIGHT + 10
                pygame.draw.rect(
                    self.screen,
                    GREEN,
                    (match_x - 5, winner_y - 2, TEAM_BOX_WIDTH + 10, TEAM_BOX_HEIGHT + 4),
                    2  # Line width
                )
    
    def draw_team_box(self, team: Team, x: int, y: int, score: int = 0):
        """Draw a box for a team with their information."""
        # Draw box
        pygame.draw.rect(
            self.screen,
            LIGHT_GRAY,
            (x, y, TEAM_BOX_WIDTH, TEAM_BOX_HEIGHT)
        )
        
        # Draw team name
        team_text = self.font.render(team.name, True, BLACK)
        team_rect = team_text.get_rect(x=x+5, centery=y+TEAM_BOX_HEIGHT//2)
        self.screen.blit(team_text, team_rect)
        
        # Draw score if available
        if score > 0:
            score_text = self.font.render(str(score), True, BLACK)
            score_rect = score_text.get_rect(right=x+TEAM_BOX_WIDTH-5, centery=y+TEAM_BOX_HEIGHT//2)
            self.screen.blit(score_text, score_rect)
    
    def draw_standings(self):
        """Draw the tournament standings."""
        # Draw section title
        title_text = self.title_font.render("Standings", True, BLACK)
        title_rect = title_text.get_rect(x=SCREEN_WIDTH - 300, y=80)
        self.screen.blit(title_text, title_rect)
        
        # Sort teams by ranking
        sorted_teams = sorted(
            self.tournament.teams,
            key=lambda team: self.tournament.standings.get(team, 999) 
        )
        
        # Draw each team's standing
        standing_y = 130
        for team in sorted_teams:
            rank = self.tournament.standings.get(team, "?")
            team_text = self.font.render(f"{rank}. {team.name}", True, BLACK)
            record_text = self.font.render(f"W-L: {team.wins}-{team.losses}", True, BLACK)
            
            self.screen.blit(team_text, (SCREEN_WIDTH - 300, standing_y))
            self.screen.blit(record_text, (SCREEN_WIDTH - 150, standing_y))
            standing_y += 30

def visualize_tournament(tournament: Tournament):
    """Create and run a visualizer for the tournament."""
    visualizer = VCTVisualizer(tournament)
    visualizer.run()

if __name__ == "__main__":
    # This module shouldn't be run directly
    print("This module should be imported and used by vct_simulator.py")
    print("Run 'python vct_simulator.py' to start the simulator.") 