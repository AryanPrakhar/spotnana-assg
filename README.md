# SkyPath

I built a flight search app that finds optimal direct and connecting itineraries while handling timezone-aware scheduling, valid layover rules, and smart route ranking.

## Running It Locally

Clean start:

```bash
docker-compose down
docker system prune -f
docker-compose up -d --build
```

Test the API:

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"origin":"JFK","destination":"LAX","date":"2024-03-15"}'
```

Visit `http://localhost:3000` in your browser, or view backend docs at `http://localhost:8000/docs`.

For iterative development:
```bash
chmod +x build_docker.sh
./build_docker.sh
```
## Development journey - in short

The initial challenge was timezone handling. I converted all flight times to UTC for calculations and back to local times for display, fixing overnight and date-line issues. NetworkX pathfinding was pruned to two stops for performance. The UI shows full dates and city names for clarity. I kept it simple with in-memory data and client-side search, leaving room to scale with a database and caching later.


## How I Built It

### Backend

A FastAPI service that loads `flights.json` at startup and exposes:
- `POST /search`: Returns sorted itineraries with flight segments, layover times, total travel time, and price, enforcing domestic/international layover rules.
- `GET /airports`: Returns all 25 airports for frontend autocomplete.

The algorithm uses a graph-based approach, modeling flights as nodes and valid connections as edges.

### Frontend

A minimal React app with:
- A search form featuring airport autocomplete
- Date picker
- Clear results display with loading states
- Client-side autocomplete for 25 airports

## My Tech Stack

### FastAPI
Chosen for rapid development, built-in validation, and security features.

### NetworkX for Pathfinding
Models flights as a directed graph, letting me focus on connection validation rather than traversal logic.

### Timezone Handling
Each flight's local times are parsed with the airport's timezone, converted to UTC for calculations, then displayed back in local time-correctly handling overnight flights and date-line crossings.

### Docker Compose
Simplifies environment setup and deployment.

### In-Memory Data
Loading `flights.json` at startup works for ~260 flights. For larger datasets, I would use something like PostgreSQL

## How It Works

### Connection Validation
`is_valid_connection()` enforces:
- Layover at the same airport
- Minimum layover: 45 minutes domestic, 90 minutes international
- Maximum layover: 6 hours
- Domestic/international determined by country

### Graph-Based Search
The system finds all paths through the flight graph with up to 2 stops, respecting connection rules.

### Ranking Strategy
Itineraries are sorted by:
1. **Total duration** - fastest overall travel time
2. **Total price** - tiebreaker for similar durations
3. **Fewest stops** - prefer directness when other factors are equal

A/B testing can be done for a better 'Recommended' ranking.

### Tradeoffs
- In-memory data - fine for demo, crashes at scale
- Brute-force search - works with small datasets, slow with millions
- No caching - identical searches recalculated
- Blocking calls - degrades under concurrent load
- Client-side airport search - doesn't scale beyond small lists

### Future Work 

- Database - PostgreSQL with indexes for flight queries
- Caching layer - Redis for popular routes
- Async processing - background jobs for complex searches
- Algorithm optimization - efficient pathfinding
- Horizontal scaling - load balancing across instances

## Assumptions

- All flight times are for `2024-03-15` or overnight to `2024-03-16`
- Maximum 2 stops (3 flight segments)

## Stack

- **Backend**: Python 3.11, FastAPI, NetworkX
- **Frontend**: React 18, Vite
- **Infrastructure**: Docker

**Super excited to join Spotnana** :)
