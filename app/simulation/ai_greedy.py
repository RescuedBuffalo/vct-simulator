from typing import Optional, Tuple
from app.simulation.models.player import Player

class GreedyAgent:
    """
    A simple greedy AI agent for controlling a Player in the simulation.
    This agent always takes the most immediately rewarding action available.
    """
    def __init__(self, player: Player):
        self.player = player

    def decide_action(self, game_state) -> dict:
        """
        Decide the next action for the player based on the current game state.
        Returns a dict describing the action (e.g., {'move': (dx, dy)}, {'shoot': target_id}, etc.)
        """
        # If not alive, do nothing
        if not self.player.alive:
            return {'action': 'idle'}

        # If can plant and has spike, plant
        if self.player.spike and self._can_plant(game_state):
            return {'action': 'plant'}

        # If can defuse and is on spike, defuse
        if self._can_defuse(game_state):
            return {'action': 'defuse'}

        # If sees an enemy, shoot at the closest one
        if self.player.visible_enemies:
            target_id = self._closest_visible_enemy(game_state)
            return {'action': 'shoot', 'target_id': target_id}

        # Otherwise, move toward objective (e.g., spike site or spike)
        move_target = self._choose_move_target(game_state)
        if move_target:
            return {'action': 'move', 'target': move_target}

        # Default: idle
        return {'action': 'idle'}

    def _can_plant(self, game_state) -> bool:
        # Placeholder: check if at plant site and round allows planting
        # Implement actual logic based on game_state
        return getattr(game_state, 'at_plant_site', False)

    def _can_defuse(self, game_state) -> bool:
        # Placeholder: check if at spike and round allows defusing
        return getattr(game_state, 'at_spike', False)

    def _closest_visible_enemy(self, game_state) -> Optional[str]:
        # Find the closest visible enemy by distance
        min_dist = float('inf')
        closest_id = None
        for enemy_id in self.player.visible_enemies:
            enemy = game_state.players.get(enemy_id)
            if enemy and enemy.alive:
                dist = self._distance(self.player.location, enemy.location)
                if dist < min_dist:
                    min_dist = dist
                    closest_id = enemy_id
        return closest_id

    def _choose_move_target(self, game_state) -> Optional[Tuple[float, float, float]]:
        # Move toward spike site if attacker, or toward spike if defender and spike is down
        if self.player.spike:
            # Move to plant site
            return getattr(game_state, 'plant_site_location', None)
        elif getattr(game_state, 'spike_location', None):
            # Move to spike if not in possession
            return game_state.spike_location
        else:
            # Move to default objective (e.g., center of map)
            return getattr(game_state, 'default_objective', None)

    def _distance(self, a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5 