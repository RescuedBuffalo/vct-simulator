What’s Present
Observation Space (What the agent “sees” at each step)
Self State:
Health, armor, alive status, location (x, y, z), direction, velocity, weapon, shield, spike possession, ability charges/cooldowns, status effects, credits, etc. (see Player dataclass).
Perception:
List of visible enemies (IDs), heard sounds (type, location, intensity), known enemy positions (from comms), known spike location, comms buffer.
Team State:
Team knowledge, map knowledge, round knowledge, team/round/map callouts and strategic points (all in Player).
Objective/Map State:
Spike planted, spike location, round timer, phase, site control (some of this is in blackboards and round state).
Economy:
Credits, inventory, buy phase info.
History/Memory:
Comms buffer, known positions, blackboard round memory, etc.
Action Space (What the agent can do at each step)
Movement:
Move direction (vector), is_walking, is_crouching, is_jumping.
Combat:
Shoot (at target), reload, switch weapon.
Ability Use:
Use ability (which, and possibly where/at whom).
Objective:
Plant, defuse, pick up spike.
Buy Phase:
Buy weapon, shield, abilities.
Communication:
Callout, ping, etc. (not yet explicit in action space, but present in comms logic).
Logging/Stats
MatchStats and Round log many events (kills, utility, site entries, etc.), but not full (obs, action, reward, done) tuples per player per tick.
What’s MISSING or INCOMPLETE for RL Logging
Observation Space Gaps
No Unified “Observation” Object:
There’s no single function or method that, given a player and the current game state, returns a serializable observation dict/array as would be fed to an RL model.
Some info is scattered (e.g., blackboard, round, player), but not all is easily accessible in one place.
Partial Observability Not Explicit:
The “observation” should only include what the player could know (not full game state). Some fields (e.g., enemy health, exact positions) may be too “omniscient” if not filtered.
Reward Signal Not Per-Tick:
Rewards are calculated at round end or on events, but not always available per tick for logging. For RL, you want to log the reward at each step (even if 0 most of the time).
Done/Terminal Flag:
No explicit “done” flag per player per tick (i.e., whether the episode/round is over for this player).
Personality/Conditioning Vector:
If you want to train with personality conditioning, the current “personality”/reward weights are not part of the observation.
Action Masking:
No explicit action mask (which actions are valid at this step), which is useful for RL frameworks.
Action Space Gaps
No Unified “Action” Object:
Actions are decided by the AI (e.g., GreedyAgent.decide_action returns a dict), but there’s no standard action encoding (e.g., a fixed dict or array with all possible action heads).
Some actions (e.g., movement, shoot, ability use) are not always mutually exclusive, but the action space is not formalized.
Action Parameters Not Standardized:
For abilities, movement, etc., the parameters (e.g., target location) are not always in a fixed format.
Buy Phase Actions:
Buy actions are simulated, but not always logged as part of the per-tick action space.
Communication Actions:
Communication is simulated, but not part of the action space (should be if you want RL to learn comms).
Logging/Replay Gaps
No Per-Tick Logging of (obs, action, reward, done):
The simulation does not currently log, for each player at each tick, the full tuple needed for RL training.
No Episode/Trajectory IDs:
For RL, you want to log match_id, round_id, player_id, and tick for each record.
No Serialization/Compression:
No code for serializing observations/actions to JSONL/Parquet, or for compressing logs.
Summary Table
| Category | Present? | Missing/Needs Improvement? |
|------------------|----------|----------------------------|
| Self State | Yes | Needs unified obs object |
| Team State | Partial | Needs filtering, unification|
| Enemy Info | Partial | Needs partial obs enforcement|
| Objective State | Partial | Needs unification |
| Economy | Yes | |
| History/Memory | Partial | Needs unification |
| Reward | Partial | Needs per-tick logging |
| Done Flag | No | Needs per-tick logging |
| Personality | No | Add to obs if conditioning |
| Action Heads | Partial | Needs unified action object|
| Action Mask | No | Add for RL frameworks |
| Buy Phase | Partial | Needs logging as actions |
| Communication | Partial | Needs to be an action head |
| Logging | Partial | Needs per-tick (obs, act, reward, done) logging |
Recommendations (Next Steps)
Implement a function (e.g., get_observation(player, game_state)) that returns a serializable dict/array of the full observation for a player at a tick, including only what they should know.
Standardize the action space: Define a fixed action dict/array for all possible actions (movement, shoot, ability, buy, comms, etc.), with parameters.
Add per-tick logging: At each simulation tick, for each player, log:
match_id, round_id, tick, player_id
observation (from above)
action (from above)
reward (for this tick)
done (is episode/round over for this player)
Add personality/conditioning vector to the observation if you want to train for different styles.
(Optional) Add action mask to the observation for RL frameworks that use it.
Ensure logs are compressed and sharded for scalability.
