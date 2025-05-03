# VCT Simulator API

## Overview
The VCT Simulator API is a backend service for managing game simulations. It is built using FastAPI and provides endpoints to manage matches, rounds, players, and more.

## Setup Instructions

### Prerequisites
- Python 3.8+
- SQLite for development (PostgreSQL for production is recommended)
- Virtual environment (optional but recommended)

### Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd vct-simulator
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the database migrations:
   ```bash
   alembic upgrade head
   ```

5. Start the FastAPI server:
   ```bash
   uvicorn app.api.main:app --reload
   ```

## API Endpoints

### Health Check
- **GET /**
  - **Description**: Check if the API is running.
  - **Response**: `{ "status": "ok", "message": "VCT Simulator API is running" }`

### Matches
- **POST /matches/**
  - **Description**: Create a new match with specified teams and map.
  - **Request Body**: `CreateMatchRequest`
    ```json
    {
      "team_a": ["player1", "player2"],
      "team_b": ["player3", "player4"],
      "map_name": "Ascent",
      "agent_assignments": {"player1": "Jett", "player2": "Sage"}
    }
    ```
  - **Response**: `MatchResponse`
    ```json
    {
      "match_id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "created"
    }
    ```

- **GET /matches/{match_id}**
  - **Description**: Get the current state of a match.
  - **Response**: `MatchStateResponse`
    ```json
    {
      "match_id": "123e4567-e89b-12d3-a456-426614174000",
      "state": "ongoing",
      "score": {"team_a": 5, "team_b": 3}
    }
    ```

- **POST /matches/{match_id}/rounds/next**
  - **Description**: Simulate the next round of the match.
  - **Response**: `RoundResponse`
    ```json
    {
      "round_number": 9,
      "winner": "team_a",
      "events": ["player1 eliminated player3"]
    }
    ```

- **GET /matches/{match_id}/rounds/{round_number}**
  - **Description**: Get the state of a specific round.
  - **Response**: `RoundStateResponse`
    ```json
    {
      "round_number": 9,
      "state": "completed",
      "events": ["player1 eliminated player3"]
    }
    ```

- **POST /matches/{match_id}/players/{player_id}/agent**
  - **Description**: Assign an agent to a player.
  - **Request Body**: `AssignAgentRequest`
    ```json
    {
      "agent_name": "Phoenix"
    }
    ```
  - **Response**: `PlayerResponse`
    ```json
    {
      "player_id": "player1",
      "agent": "Phoenix"
    }
    ```

- **POST /matches/{match_id}/players/{player_id}/ai**
  - **Description**: Assign an AI agent to a player.
  - **Request Body**: `AssignAIRequest`
    ```json
    {
      "ai_type": "aggressive",
      "skill_level": 5
    }
    ```
  - **Response**: `PlayerResponse`
    ```json
    {
      "player_id": "player1",
      "ai_type": "aggressive",
      "skill_level": 5
    }
    ```

### Maps
- **GET /maps/**
  - **Description**: Get a list of available maps.
  - **Response**: `List[str]`
    ```json
    ["Ascent", "Bind", "Haven"]
    ```

### Agents
- **GET /agents/**
  - **Description**: Get a list of available agents.
  - **Response**: `List[str]`
    ```json
    ["Jett", "Sage", "Phoenix"]
    ```

### AI Types
- **GET /ai_types/**
  - **Description**: Get a list of available AI agent types.
  - **Response**: `List[str]`
    ```json
    ["aggressive", "defensive", "balanced"]
    ```

### Match Statistics
- **GET /matches/{match_id}/stats**
  - **Description**: Get detailed statistics for a match.
  - **Response**: `MatchStatsResponse`
    ```json
    {
      "match_id": "123e4567-e89b-12d3-a456-426614174000",
      "team_a_stats": {"kills": 10, "deaths": 5},
      "team_b_stats": {"kills": 5, "deaths": 10}
    }
    ```

## Testing

To run the test suite, use the following command:
```bash
pytest
```
This will execute all tests, including those for match creation, state retrieval, round simulation, and player assignments.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
