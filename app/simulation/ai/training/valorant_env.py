import gymnasium as gym
import numpy as np
from typing import Dict, Tuple, Optional, Any
from ...models.player import Player
from ...models.team import Team
from ...models.round import Round, RoundPhase, RoundWinner, RoundEndCondition, ROUND_TIMER, BUY_PHASE_TIMER
from ...models.map import Map
from ...models.weapon import WeaponFactory, BuyPreferences
from ...models.ability import AbilityDefinition, AbilityInstance, create_flash_ability, create_smoke_ability, create_molly_ability
from ..agents.base import AgentConfig
from .rewards import RewardFunctions

class ValorantEnv(gym.Env):
    """
    Valorant simulator environment for reinforcement learning.
    Implements the gymnasium interface for RL training.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the environment.
        
        Args:
            config: Dictionary containing:
                - role: The agent's role (duelist, controller, sentinel, initiator)
                - map_name: Name of the map to play on
                - team_size: Number of players per team
                - max_rounds: Maximum number of rounds per match
                - personality: Optional personality traits for conditioning
        """
        super().__init__()
        
        self.config = config
        self.role = config['role']
        self.map_name = config.get('map_name', 'ascent')
        self.team_size = config.get('team_size', 5)
        self.max_rounds = config.get('max_rounds', 25)
        self.personality = config.get('personality', {
            'aggression': 0.5,
            'patience': 0.5,
            'teamplay': 0.5
        })
        
        # Create map
        self.map = Map(self.map_name, 32, 32)  # Default size, should be configured per map
        
        # Initialize weapon system
        self.weapon_catalog = WeaponFactory.create_weapon_catalog()
        
        # Initialize teams and blackboards
        self.current_team = Team("Attackers", "Attackers")
        self.opponent_team = Team("Defenders", "Defenders")
        
        # Create the agent player with configuration
        self.current_player = self._create_player(
            id="RL_Agent",
            name="RL_Agent",
            team=self.current_team,
            role=self.role,
            skill_level=0.7
        )
        
        # Add agent to team
        self.current_team.add_player(self.current_player)
        
        # Add AI teammates and opponents
        self._populate_teams()
        
        # Set up reward functions
        self.reward_functions = RewardFunctions()
        
        # Track episode stats
        self.episode_stats = {
            'kills': 0,
            'deaths': 0,
            'assists': 0,
            'damage_dealt': 0,
            'rounds_won': 0,
            'objectives_completed': 0,
            'utility_value': 0
        }
        
        # Initialize round state
        self.round = None  # Will be created in reset()
        
        # Define observation and action spaces
        self._setup_observation_space()
        self._setup_action_space()
    
    def _create_player(self, id: str, name: str, team: Team, role: str, skill_level: float) -> Player:
        """Create a player with appropriate abilities and stats."""
        player = Player(
            id=id,
            name=name,
            team_id=team.id,
            role=role,
            agent=role,  # Use role as agent type for now
            aim_rating=skill_level * 100,
            reaction_time=200.0,
            movement_accuracy=skill_level * 100,
            spray_control=skill_level * 100,
            clutch_iq=skill_level * 100
        )
        
        # Set up default abilities based on role
        if role == "duelist":
            player.utility_charges = {
                "flash": 2,
                "entry": 1,
                "mobility": 2,
                "ultimate": 0
            }
            player.abilities = {
                "flash": create_flash_ability("Entry Flash"),
                "smoke": create_smoke_ability("Cover Smoke"),
                "molly": create_molly_ability("Clear Molly")
            }
        elif role == "controller":
            player.utility_charges = {
                "smoke": 3,
                "slow": 2,
                "molly": 1,
                "ultimate": 0
            }
            player.abilities = {
                "smoke": create_smoke_ability("Control Smoke", duration=20.0),
                "molly": create_molly_ability("Area Denial")
            }
        elif role == "sentinel":
            player.utility_charges = {
                "trap": 2,
                "slow": 2,
                "info": 1,
                "ultimate": 0
            }
            player.abilities = {
                "trap": create_molly_ability("Trap", damage=5.0),
                "slow": create_smoke_ability("Slow Field", duration=10.0)
            }
        elif role == "initiator":
            player.utility_charges = {
                "flash": 2,
                "recon": 1,
                "breach": 2,
                "ultimate": 0
            }
            player.abilities = {
                "flash": create_flash_ability("Info Flash"),
                "recon": create_smoke_ability("Recon", duration=5.0)
            }
        
        return player
    
    def _setup_observation_space(self):
        """Set up the observation space based on what our simulation can provide."""
        # Get a sample observation to determine space size
        sample_obs = self.current_player.get_observation(
            round_obj=None,
            team_blackboard=self.current_team.blackboard,
            personality=self.personality
        )
        flat_obs = self._flatten_observation(sample_obs)
        
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(len(flat_obs),),
            dtype=np.float32
        )

    def _setup_action_space(self):
        """Set up the action space based on available mechanics."""
        self.action_space = gym.spaces.Dict({
            'action_type': gym.spaces.Discrete(7),  # move, shoot, plant, defuse, buy, use_ability, communicate
            'move': gym.spaces.Dict({
                'direction': gym.spaces.Box(low=-1, high=1, shape=(2,)),  # 2D movement direction
                'is_walking': gym.spaces.Discrete(2),
                'is_crouching': gym.spaces.Discrete(2),
                'is_jumping': gym.spaces.Discrete(2)
            }),
            'shoot': gym.spaces.Dict({
                'target_direction': gym.spaces.Box(low=-1, high=1, shape=(2,)),  # 2D aim direction
                'trigger_pull': gym.spaces.Discrete(2),
                'is_scoped': gym.spaces.Discrete(2),
                'burst_length': gym.spaces.Discrete(4)  # 0=tap, 1=burst, 2=medium spray, 3=full spray
            }),
            'buy': gym.spaces.Dict({
                'weapon_type': gym.spaces.Discrete(len(self.weapon_catalog)),
                'shield_type': gym.spaces.Discrete(3),   # None, Light, Heavy
                'abilities': gym.spaces.MultiBinary(4)   # Which abilities to buy
            }),
            'use_ability': gym.spaces.Dict({
                'ability_slot': gym.spaces.Discrete(4),  # Which ability to use (C, Q, E, X)
                'target_location': gym.spaces.Box(low=-1, high=1, shape=(2,)),  # Where to use ability
                'charge_time': gym.spaces.Box(low=0, high=1, shape=(1,))  # For chargeable abilities
            }),
            'communicate': gym.spaces.Dict({
                'comm_type': gym.spaces.Discrete(5),  # ping, voice line, request, strategy, info
                'target_location': gym.spaces.Box(low=-1, high=1, shape=(2,)),
                'message_id': gym.spaces.Discrete(20)  # Different preset messages
            })
        })

    def _populate_teams(self):
        """Add AI players to both teams."""
        for i in range(self.team_size - 1):
            # Add teammates with varied roles
            teammate = Player(
                id=f"Teammate_{i}",
                name=f"Teammate_{i}",
                team_id=self.current_team.id,
                role=self._get_complementary_role(i),
                agent=self._get_complementary_role(i),
                aim_rating=70.0,
                reaction_time=200.0,
                movement_accuracy=70.0,
                spray_control=70.0,
                clutch_iq=70.0
            )
            self.current_team.add_player(teammate)
            
            # Add opponents
            opponent = Player(
                id=f"Opponent_{i}",
                name=f"Opponent_{i}",
                team_id=self.opponent_team.id,
                role=self._get_complementary_role(i),
                agent=self._get_complementary_role(i),
                aim_rating=70.0,
                reaction_time=200.0,
                movement_accuracy=70.0,
                spray_control=70.0,
                clutch_iq=70.0
            )
            self.opponent_team.add_player(opponent)
    
    def _get_complementary_role(self, index: int) -> str:
        """Get a complementary role based on index to create a balanced team."""
        roles = ["duelist", "controller", "sentinel", "initiator"]
        if self.role in roles:
            roles.remove(self.role)
        return roles[index % len(roles)]
    
    def reset(self, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict]:
        """Reset the environment to start a new episode."""
        super().reset(seed=seed)
        
        # Reset teams
        self.current_team.reset()
        self.opponent_team.reset()
        
        # Create a new round
        all_players = {p.id: p for p in self.current_team.players + self.opponent_team.players}
        attacker_ids = [p.id for p in self.current_team.players]
        defender_ids = [p.id for p in self.opponent_team.players]
        
        self.round = Round(
            round_number=1,
            players=all_players,
            attacker_ids=attacker_ids,
            defender_ids=defender_ids,
            map_obj=self.map,
            attacker_blackboard=self.current_team.blackboard,
            defender_blackboard=self.opponent_team.blackboard,
            seed=seed
        )
        
        # Reset episode stats
        self.episode_stats = {k: 0 for k in self.episode_stats}
        
        # Get initial observation
        observation = self._get_observation()
        
        return observation, {}
    
    def step(self, action: Dict) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Take a step in the environment.
        
        Args:
            action: Action from the agent
            
        Returns:
            observation: Current observation
            reward: Reward from the action
            terminated: Whether episode is done
            truncated: Whether episode was truncated
            info: Additional information
        """
        # Apply action to player
        self._apply_action(action)
        
        # Update round state
        self.round.update(time_step=0.5)  # 0.5 second timestep
        
        # Get new observation
        observation = self._get_observation()
        
        # Calculate reward
        reward = self._calculate_reward()
        
        # Check if episode is done
        done = self._is_episode_done()
        
        # Get additional info
        info = self._get_info()
        
        return observation, reward, done, False, info
    
    def _get_observation(self) -> np.ndarray:
        """Get the current observation using the Player model's get_observation method."""
        raw_obs = self.current_player.get_observation(
            round_obj=self.round,
            team_blackboard=self.current_team.blackboard,
            personality=self.personality
        )
        return self._flatten_observation(raw_obs)
    
    def _flatten_observation(self, obs: Dict) -> np.ndarray:
        """Convert the hierarchical observation dict into a flat numpy array."""
        flat_obs = []
        
        # Player State
        flat_obs.extend([
            obs['health'] / 100.0,
            obs['armor'] / 100.0,
            obs['creds'] / 9000.0,
            float(obs['alive']),
            float(obs['is_planting']),
            float(obs['is_defusing']),
            obs['plant_progress'] / ROUND_TIMER,
            obs['defuse_progress'] / ROUND_TIMER
        ])
        
        # Position and Movement
        flat_obs.extend([
            obs['location'][0] / self.map.width,
            obs['location'][1] / self.map.height,
            obs['location'][2] / 5.0,  # Normalize height
            obs['direction'] / 360.0,
            float(obs['is_walking']),
            float(obs['is_crouching']),
            float(obs['is_jumping']),
            float(obs['ground_contact'])
        ])
        
        # Velocity and Physics
        velocity = obs.get('velocity', (0.0, 0.0, 0.0))
        flat_obs.extend([
            velocity[0] / 10.0,  # Normalize by max speed
            velocity[1] / 10.0,
            velocity[2] / 10.0
        ])
        
        # Equipment and Resources
        weapon_onehot = np.zeros(len(self.weapon_catalog))
        if obs['weapon']:
            weapon_idx = list(self.weapon_catalog.keys()).index(obs['weapon'])
            weapon_onehot[weapon_idx] = 1.0
        flat_obs.extend(weapon_onehot)
        
        shield_onehot = np.zeros(3)  # [none, light, heavy]
        if obs['shield'] == 'light':
            shield_onehot[1] = 1.0
        elif obs['shield'] == 'heavy':
            shield_onehot[2] = 1.0
        else:
            shield_onehot[0] = 1.0
        flat_obs.extend(shield_onehot)
        
        # Abilities
        ability_charges = np.zeros(4)  # Normalized ability charges
        for i, (ability, charges) in enumerate(obs['utility_charges'].items()):
            if i < 4:  # Only consider first 4 abilities
                ability_charges[i] = charges / 2.0  # Normalize by max charges
        flat_obs.extend(ability_charges)
        
        # Game State
        phase_onehot = np.zeros(3)  # [buy, round, end]
        if obs['phase']:
            phase_idx = {'buy': 0, 'round': 1, 'end': 2}.get(obs['phase'], 0)
            phase_onehot[phase_idx] = 1.0
        flat_obs.extend(phase_onehot)
        
        # Round Info
        flat_obs.extend([
            obs['round_time_remaining'] / ROUND_TIMER if obs['round_time_remaining'] is not None else 0.0,
            float(obs['spike_planted']),
            obs['spike_time_remaining'] / ROUND_TIMER if obs['spike_time_remaining'] is not None else 0.0
        ])
        
        # Team State
        flat_obs.extend([
            len(obs['team_alive']) / self.team_size,
            obs['team_confidence'] if obs['team_confidence'] is not None else 0.5
        ])
        
        # Map Control (from blackboard)
        if 'cleared_areas' in obs and 'danger_areas' in obs:
            map_control = np.zeros(len(self.map.areas))
            for area in obs['cleared_areas']:
                area_idx = list(self.map.areas.keys()).index(area)
                map_control[area_idx] = 1.0
            for area in obs['danger_areas']:
                area_idx = list(self.map.areas.keys()).index(area)
                map_control[area_idx] = -1.0
            flat_obs.extend(map_control)
        
        # Enemy Information
        visible_enemies = np.zeros(self.team_size)
        enemy_positions = np.zeros((self.team_size, 2))
        enemy_healths = np.zeros(self.team_size)
        
        for i, enemy_id in enumerate(obs['visible_enemies'][:self.team_size]):
            visible_enemies[i] = 1.0
            if enemy_id in obs['known_enemy_positions']:
                pos = obs['known_enemy_positions'][enemy_id]
                enemy_positions[i] = [
                    pos[0] / self.map.width,
                    pos[1] / self.map.height
                ]
        
        flat_obs.extend(visible_enemies)
        flat_obs.extend(enemy_positions.flatten())
        flat_obs.extend(enemy_healths)
        
        # Sound Information
        heard_sounds = np.zeros((5, 3))  # Up to 5 recent sounds, each with [type, x, y]
        for i, sound in enumerate(obs['heard_sounds'][:5]):
            sound_type = {'footstep': 0, 'gunshot': 1, 'ability': 2}.get(sound['type'], 3)
            heard_sounds[i] = [
                sound_type / 3.0,
                sound['location'][0] / self.map.width,
                sound['location'][1] / self.map.height
            ]
        flat_obs.extend(heard_sounds.flatten())
        
        return np.array(flat_obs, dtype=np.float32)
    
    def _apply_action(self, action: Dict):
        """Apply the agent's action to the player state."""
        action_type = action['action_type']
        
        if action_type == 0:  # move
            direction = action['move']['direction']
            self.current_player.set_movement_input(
                direction=direction,
                is_walking=bool(action['move']['is_walking']),
                is_crouching=bool(action['move']['is_crouching']),
                is_jump_pressed=bool(action['move']['is_jumping'])
            )
        
        elif action_type == 1:  # shoot
            if self.current_player.visible_enemies:
                target_id = self.current_player.visible_enemies[0]
                # Apply shooting modifiers
                accuracy_modifier = 1.0
                if action['shoot']['is_scoped']:
                    accuracy_modifier *= 1.2
                if action['shoot']['burst_length'] > 1:
                    accuracy_modifier *= 0.8
                # Get weapon stats
                weapon = self.weapon_catalog.get(self.current_player.weapon)
                if weapon:
                    accuracy_modifier *= weapon.accuracy
                    if self.current_player.is_moving:
                        accuracy_modifier *= weapon.movement_accuracy
                # Simulate combat with modifiers
                self.round._simulate_duel(
                    self.current_player.id,
                    target_id,
                    accuracy_modifier=accuracy_modifier
                )
        
        elif action_type == 2:  # plant
            if not self.current_player.is_planting and self.current_player.spike:
                self.current_player.start_plant(self.round)
        
        elif action_type == 3:  # defuse
            if not self.current_player.is_defusing and self.round.spike_planted:
                self.current_player.start_defuse(self.round)
        
        elif action_type == 4:  # buy
            if self.round.phase == RoundPhase.BUY:
                self._handle_buy_action(action['buy'])
        
        elif action_type == 5:  # use_ability
            ability_slot = action['use_ability']['ability_slot']
            if ability_slot < len(self.current_player.utility_charges):
                ability_name = list(self.current_player.utility_charges.keys())[ability_slot]
                if self.current_player.utility_charges[ability_name] > 0:
                    target_location = (
                        action['use_ability']['target_location'][0] * self.map.width,
                        action['use_ability']['target_location'][1] * self.map.height
                    )
                    # Use ability through round's ability system
                    self.round._use_ability(
                        self.current_player.id,
                        ability_name,
                        target_location,
                        charge_time=float(action['use_ability']['charge_time'])
                    )
        
        elif action_type == 6:  # communicate
            comm_type = action['communicate']['comm_type']
            message = self._get_comm_message(
                comm_type,
                action['communicate']['message_id']
            )
            if message:
                self.round._log_comm_event(
                    self.current_player.id,
                    message,
                    target_location=(
                        action['communicate']['target_location'][0] * self.map.width,
                        action['communicate']['target_location'][1] * self.map.height
                    )
                )
    
    def _handle_buy_action(self, buy_action: Dict):
        """Handle buy actions with enhanced weapon selection."""
        # Get weapon from catalog
        weapon_list = list(self.weapon_catalog.keys())
        weapon_type = buy_action['weapon_type']
        if weapon_type < len(weapon_list):
            weapon_name = weapon_list[weapon_type]
            weapon = self.weapon_catalog[weapon_name]
            if self.current_player.creds >= weapon.cost:
                self.current_player.weapon = weapon_name
                self.current_player.creds -= weapon.cost
        
        # Shield purchase
        shield_costs = {1: 400, 2: 1000}  # light, heavy
        shield_type = buy_action['shield_type']
        if shield_type in shield_costs and self.current_player.creds >= shield_costs[shield_type]:
            self.current_player.shield = 'light' if shield_type == 1 else 'heavy'
            self.current_player.creds -= shield_costs[shield_type]
        
        # Ability purchase
        ability_costs = {
            0: 200,  # Basic ability 1
            1: 200,  # Basic ability 2
            2: 300,  # Signature ability
            3: 0     # Ultimate (uses ult points instead)
        }
        
        for ability_idx, should_buy in enumerate(buy_action['abilities']):
            if should_buy:
                if ability_idx < 3:  # Regular abilities
                    if self.current_player.creds >= ability_costs[ability_idx]:
                        self.current_player.utility_charges[f"ability_{ability_idx}"] = 1
                        self.current_player.creds -= ability_costs[ability_idx]
                elif ability_idx == 3:  # Ultimate
                    if self.current_player.ult_points >= 7:
                        self.current_player.utility_charges["ultimate"] = 1
                        self.current_player.ult_points -= 7

    def _get_comm_message(self, comm_type: int, message_id: int) -> Optional[str]:
        """Get communication message based on type and ID."""
        comm_messages = {
            0: {  # Pings
                0: "Enemy spotted",
                1: "Caution here",
                2: "Watching here",
                3: "Need help here",
                4: "Rush here"
            },
            1: {  # Voice lines
                0: "Nice!",
                1: "Thanks",
                2: "Sorry",
                3: "Well done"
            },
            2: {  # Requests
                0: "Need healing",
                1: "Need weapons",
                2: "Save",
                3: "Eco round"
            },
            3: {  # Strategy
                0: "Let's split",
                1: "Play for picks",
                2: "Rush site",
                3: "Default setup"
            },
            4: {  # Info
                0: "Rotating",
                1: "Walking",
                2: "Low HP",
                3: "Ultimate ready"
            }
        }
        
        return comm_messages.get(comm_type, {}).get(message_id)
    
    def _calculate_reward(self) -> float:
        """Calculate the reward using role-specific reward functions."""
        # Get round state information
        state = {
            'round_won': self.round.round_winner == RoundWinner.ATTACKERS if self.current_player.id in self.round.attacker_ids else self.round.round_winner == RoundWinner.DEFENDERS,
            'round_lost': self.round.round_winner != RoundWinner.NONE and not state['round_won'],
            'survived_round': self.current_player.alive,
            'entry_kill': len(self.round._death_events) == 1 and self.round._death_events[0].killer_id == self.current_player.id,
            'utility_damage': 0,  # Would need to track from ability effects
            'space_created': False,  # Would need map control tracking
            'area_denied': False,  # Would need map control tracking
            'site_control': False,  # Would need map control tracking
            'enemy_detected': bool(self.current_player.visible_enemies),
            'teammate_protected': False,  # Would need more sophisticated tracking
            'flash_assist': False,  # Would need ability tracking
        }
        
        if self.role == "duelist":
            reward = self.reward_functions.duelist_reward(state, self.episode_stats)
        elif self.role == "controller":
            reward = self.reward_functions.controller_reward(state, self.episode_stats)
        elif self.role == "sentinel":
            reward = self.reward_functions.sentinel_reward(state, self.episode_stats)
        elif self.role == "initiator":
            reward = self.reward_functions.initiator_reward(state, self.episode_stats)
            
        # Add common rewards
        reward += self.reward_functions.common_reward(state, self.episode_stats)
        
        return reward
    
    def _is_episode_done(self) -> bool:
        """Check if the episode is complete."""
        return (
            not self.current_player.alive or
            self.round.phase == RoundPhase.END
        )
    
    def _get_info(self) -> Dict:
        """Get additional information about the current state."""
        return {
            'episode_stats': self.episode_stats,
            'player_stats': {
                'kills': self.current_player.kills,
                'deaths': self.current_player.deaths,
                'assists': self.current_player.assists,
                'damage_dealt': self.current_player.damage_dealt
            },
            'round_phase': self.round.phase.value,
            'round_time': self.round.round_time_remaining,
            'spike_planted': self.round.spike_planted,
            'spike_time': self.round.spike_time_remaining
        } 