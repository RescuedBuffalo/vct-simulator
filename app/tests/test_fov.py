import unittest
import math
from app.simulation.models.player import Player
from app.simulation.models.map import Map, MapBoundary

class TestFieldOfVision(unittest.TestCase):
    def setUp(self):
        """Set up a test environment with a simple map and players."""
        # Create a simple map for testing
        self.map = Map(name="Test Map", width=100, height=100)
        
        # Place a horizontal wall blocking the line between x=20 and x=60 at y=20
        wall1 = MapBoundary(x=40, y=19, width=20, height=2, boundary_type="wall", name="wall1")
        self.map.add_boundary(wall1)
        
        # Create test players
        self.player1 = Player(
            id="p1",
            name="Player 1",
            team_id="team1",
            role="duelist",
            agent="jett",
            aim_rating=80,
            reaction_time=200,
            movement_accuracy=70,
            spray_control=75,
            clutch_iq=65,
            location=(20, 20, 0),
            direction=0  # facing east (positive x)
        )
        
        self.player2 = Player(
            id="p2",
            name="Player 2",
            team_id="team2",
            role="sentinel",
            agent="cypher",
            aim_rating=75,
            reaction_time=220,
            movement_accuracy=65,
            spray_control=70,
            clutch_iq=80,
            location=(30, 20, 0),
            direction=180  # facing west (negative x)
        )
        
        self.player3 = Player(
            id="p3",
            name="Player 3",
            team_id="team2",
            role="controller",
            agent="omen",
            aim_rating=70,
            reaction_time=210,
            movement_accuracy=75,
            spray_control=65,
            clutch_iq=75,
            location=(60, 20, 0),
            direction=180  # facing west (negative x)
        )
        
        self.player4 = Player(
            id="p4",
            name="Player 4",
            team_id="team2",
            role="initiator", 
            agent="sova",
            aim_rating=72,
            reaction_time=205,
            movement_accuracy=68,
            spray_control=70,
            clutch_iq=78,
            location=(20, 50, 0),
            direction=0  # facing east (positive x)
        )
        
        self.all_players = [self.player1, self.player2, self.player3, self.player4]
    
    def test_basic_visibility(self):
        """Test basic visibility calculation between two facing players."""
        # Player 1 and Player 2 are facing each other and should be visible
        visible_to_p1 = self.map.calculate_player_fov(self.player1, self.all_players)
        visible_to_p2 = self.map.calculate_player_fov(self.player2, self.all_players)
        
        # Check if player2 is visible to player1
        self.assertIn(self.player2, visible_to_p1)
        # Check if player1 is visible to player2
        self.assertIn(self.player1, visible_to_p2)
        
        # Players should be looking at each other
        self.assertTrue(self.player1.is_looking_at_player)
        self.assertTrue(self.player2.is_looking_at_player)
    
    def test_wall_occlusion(self):
        """Test that walls block visibility."""
        # Player 1 should not see Player 3 because there's a wall between them
        visible_to_p1 = self.map.calculate_player_fov(self.player1, self.all_players)
        
        # Check that player3 is not visible to player1 due to wall
        self.assertNotIn(self.player3, visible_to_p1)
    
    def test_angle_limits(self):
        """Test that players outside the FOV angle are not visible."""
        # Player 1 should not see Player 4 because Player 4 is at a 90° angle (to the south)
        visible_to_p1 = self.map.calculate_player_fov(self.player1, self.all_players)
        
        # Check that player4 is not visible to player1 due to FOV angle
        self.assertNotIn(self.player4, visible_to_p1)
        
        # Now turn player1 to face south
        self.player1.direction = 90
        visible_to_p1_after_turn = self.map.calculate_player_fov(self.player1, self.all_players)
        
        # Now player4 should be visible
        self.assertIn(self.player4, visible_to_p1_after_turn)
    
    def test_smoke_effect(self):
        """Test that smoke blocks visibility."""
        # Initially, player1 and player2 can see each other
        visible_to_p1 = self.map.calculate_player_fov(self.player1, self.all_players)
        self.assertIn(self.player2, visible_to_p1)
        
        # Add a smoke effect between them
        self.map.add_effect(
            effect_type="smoke",
            position=(25, 20, 0),  # Between player1 and player2
            radius=3.0,
            duration=10.0
        )
        
        # Now check visibility again
        visible_to_p1_with_smoke = self.map.calculate_player_fov(self.player1, self.all_players)
        
        # Player2 should no longer be visible through the smoke
        self.assertNotIn(self.player2, visible_to_p1_with_smoke)
    
    def test_update_player_visibility(self):
        """Test the update_player_visibility method."""
        # Initially, set visible_enemies to something that will change
        self.player1.visible_enemies = ["dummy"]
        
        # Update visibility for all players
        self.map.update_player_visibility(self.all_players)
        
        # Check that player1's visible_enemies was updated correctly
        # Only player2 and player3 are on the enemy team
        expected_visible = ["p2"]  # Only player2 should be visible (player3 is behind wall)
        self.assertEqual(self.player1.visible_enemies, expected_visible)

if __name__ == "__main__":
    unittest.main() 