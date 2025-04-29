import os
import torch
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from stable_baselines3.common.monitor import Monitor
from pathlib import Path

from .valorant_env import ValorantEnv

def make_env(role: str, map_name: str = 'ascent'):
    """Create a wrapped environment instance."""
    def _init():
        env = ValorantEnv({
            'role': role,
            'map_name': map_name,
            'team_size': 5,
            'max_rounds': 25
        })
        return Monitor(env)
    return _init

def train_agent(
    role: str,
    total_timesteps: int = 1_000_000,
    eval_freq: int = 10000,
    n_eval_episodes: int = 5,
    save_freq: int = 10000,
    map_name: str = 'ascent'
):
    """
    Train an RL agent for a specific role.
    
    Args:
        role: Agent role (duelist, controller, sentinel, initiator)
        total_timesteps: Total number of training timesteps
        eval_freq: How often to evaluate the agent
        n_eval_episodes: Number of episodes for evaluation
        save_freq: How often to save model checkpoints
        map_name: Name of the map to train on
    """
    # Create output directories
    model_dir = Path(__file__).parent.parent / 'models'
    log_dir = Path(__file__).parent.parent / 'logs'
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    
    # Create vectorized environment
    env = DummyVecEnv([make_env(role, map_name)])
    env = VecNormalize(env, norm_obs=True, norm_reward=True)
    
    # Create evaluation environment
    eval_env = DummyVecEnv([make_env(role, map_name)])
    eval_env = VecNormalize(env, norm_obs=True, norm_reward=True)
    
    # Initialize model
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log=str(log_dir),
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        device='cuda' if torch.cuda.is_available() else 'cpu'
    )
    
    # Setup callbacks
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=str(model_dir / f"{role}_best"),
        log_path=str(log_dir),
        eval_freq=eval_freq,
        deterministic=True,
        render=False,
        n_eval_episodes=n_eval_episodes
    )
    
    checkpoint_callback = CheckpointCallback(
        save_freq=save_freq,
        save_path=str(model_dir / f"{role}_checkpoints"),
        name_prefix=role
    )
    
    # Train the agent
    model.learn(
        total_timesteps=total_timesteps,
        callback=[eval_callback, checkpoint_callback],
        tb_log_name=f"{role}_training"
    )
    
    # Save final model
    model.save(str(model_dir / f"{role}_final"))
    env.save(str(model_dir / f"{role}_env"))
    
    return model

def main():
    """Train agents for all roles."""
    roles = ['duelist', 'controller', 'sentinel', 'initiator']
    maps = ['ascent', 'bind', 'haven', 'split']  # Add more maps as needed
    
    for role in roles:
        print(f"\nTraining {role} agent...")
        for map_name in maps:
            print(f"Training on {map_name}...")
            train_agent(
                role=role,
                map_name=map_name,
                total_timesteps=1_000_000,  # Adjust based on performance
                eval_freq=10000,
                n_eval_episodes=5,
                save_freq=10000
            )

if __name__ == "__main__":
    main()
