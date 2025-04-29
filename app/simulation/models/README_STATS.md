# Statistics System Documentation

The VCT simulator includes a comprehensive statistics tracking system spread across three main components: Player Stats, Team Stats, and Match Stats.

## Player Statistics (`player_stats.py`)

### Core Metrics
- **Combat Performance**
  - K/D/A (Kills/Deaths/Assists)
  - Headshot percentage
  - First blood rate
  - Trade kill efficiency
  - Average damage per round (ADR)
  - Clutch success rate

- **Economy Management**
  - Average credits per round
  - Buy round success rate
  - Eco round impact
  - Weapon preference patterns
  - Save round effectiveness

- **Utility Usage**
  - Ability usage frequency
  - Flash assist rate
  - Damage from abilities
  - Site entry success rate
  - Ultimate point generation

### Usage Example
```python
# Access player stats
player_stats = player.stats

# Combat metrics
kda = player_stats.get_kda_ratio()
adr = player_stats.get_average_damage_per_round()
hs_pct = player_stats.get_headshot_percentage()

# Economy analysis
eco_impact = player_stats.calculate_eco_round_impact()
buy_success = player_stats.get_buy_round_success_rate()
```

## Team Statistics (`team_stats.py`)

### Team Performance Metrics
- **Round Statistics**
  - Attack/Defense round win rates
  - Post-plant win percentage
  - Retake success rate
  - Round conversion rate
  - Timeout effectiveness

- **Economy Tracking**
  - Team economy rating
  - Force buy success rate
  - Save round coordination
  - Equipment value efficiency
  - Ultimate economy management

- **Strategic Metrics**
  - Site hit preferences
  - Rotation timing
  - Trade efficiency
  - Map control percentage
  - Utility coordination score

### Implementation
```python
# Team performance analysis
team_stats = team.stats

# Round analysis
attack_wr = team_stats.get_attack_win_rate()
defense_wr = team_stats.get_defense_win_rate()
post_plant = team_stats.get_post_plant_win_rate()

# Strategic analysis
site_pref = team_stats.get_site_hit_distribution()
trade_eff = team_stats.calculate_trade_efficiency()
```

## Match Statistics (`match_stats.py`)

### Match Analysis
- **Overall Performance**
  - Round distribution
  - Score progression
  - Side advantage calculation
  - Momentum shifts
  - Critical rounds identification

- **Comparative Analysis**
  - Team economy differentials
  - Utility usage comparison
  - Site control heat maps
  - Duelist performance comparison
  - Support impact analysis

- **Time-based Analysis**
  - Round duration patterns
  - Spike plant timing
  - Rotation speed
  - First contact timing
  - Ultimate usage timing

### Data Collection
```python
# Match analysis
match_stats = match.stats

# Performance analysis
score_prog = match_stats.get_score_progression()
momentum = match_stats.analyze_momentum_shifts()
economy_diff = match_stats.get_economy_differential()

# Detailed round analysis
round_summary = match_stats.get_round_summary(round_number)
```

## Integration Points

### Real-time Updates
Statistics are updated in real-time during simulation:
1. Combat events trigger stat updates
2. Round end triggers aggregation
3. Match end compiles final statistics

### Data Export
Statistics can be exported in various formats:
- JSON for data analysis
- CSV for spreadsheet analysis
- Formatted reports for presentation

### Visualization Support
The stats system supports various visualization methods:
- Heat maps for positioning
- Time series for performance
- Radar charts for player comparison
- Bar graphs for round analysis

## Best Practices

1. **Consistent Updates**
   - Update stats immediately after events
   - Use appropriate aggregation methods
   - Maintain data consistency across stats objects

2. **Performance Optimization**
   - Cache frequently accessed metrics
   - Use efficient data structures
   - Implement lazy calculation for complex metrics

3. **Data Validation**
   - Verify stat updates
   - Check for reasonable ranges
   - Handle edge cases appropriately

## Future Enhancements

Planned improvements to the stats system:
- Advanced performance metrics
- Machine learning integration
- Real-time analysis tools
- Enhanced visualization options
- Custom metric definition support
- Historical trend analysis 