from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from datetime import datetime, date, timedelta
from typing import List, Optional
import os
import networkx as nx
from zoneinfo import ZoneInfo

app = FastAPI(title="SkyPath Flight Search API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    # Allow all origins for local development
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Airport(BaseModel):
    code: str
    name: str
    city: str
    country: str
    timezone: str

class Flight(BaseModel):
    flightNumber: str
    airline: str
    origin: str
    destination: str
    departureTime: str
    arrivalTime: str
    price: float
    aircraft: str

class FlightSegment(BaseModel):
    flight: Flight
    duration_minutes: int

class Itinerary(BaseModel):
    flights: List[FlightSegment]
    total_duration_minutes: int
    total_price: float
    layovers: List[dict] = []

class SearchRequest(BaseModel):
    origin: str
    destination: str
    date: str

airports = {}
flights = []
flight_graph = nx.DiGraph()

def load_flight_data():
    global airports, flights, flight_graph
    
    flights_file = "/app/flights.json"
    if not os.path.exists(flights_file):
        flights_file = "../flights.json" 
    
    with open(flights_file, 'r') as f:
        data = json.load(f)
        
    airports = {airport['code']: Airport(**airport) for airport in data['airports']}
    flights = [Flight(**flight) for flight in data['flights']]
    build_flight_graph()

def build_flight_graph():
    """Build networkx graph of flights for connection search"""
    global flight_graph
    flight_graph = nx.DiGraph()
    
    # Add all airports as nodes
    for airport_code in airports.keys():
        flight_graph.add_node(airport_code)
    
    # Add flights as edges with flight data
    for flight in flights:
        flight_graph.add_edge(
            flight.origin, 
            flight.destination, 
            flight_data=flight,
            departure_time=flight.departureTime,
            arrival_time=flight.arrivalTime
        )

def to_utc_datetime(local_time_str: str, airport_code: str) -> datetime:
    """Convert local airport time to UTC datetime"""
    if airport_code not in airports:
        raise ValueError(f"Unknown airport: {airport_code}")
    
    airport = airports[airport_code]
    timezone = ZoneInfo(airport.timezone)
    
    local_dt = datetime.fromisoformat(local_time_str)
    local_dt_with_tz = local_dt.replace(tzinfo=timezone)
    
    return local_dt_with_tz.astimezone(ZoneInfo('UTC'))

def calculate_duration(departure_time: str, departure_airport: str, 
                      arrival_time: str, arrival_airport: str) -> int:
    """Calculate flight duration using UTC conversion"""
    dept_utc = to_utc_datetime(departure_time, departure_airport)
    arr_utc = to_utc_datetime(arrival_time, arrival_airport)
    
    duration_minutes = int((arr_utc - dept_utc).total_seconds() / 60)
    
    if duration_minutes < 0:
        duration_minutes += 24 * 60
    
    return duration_minutes

def is_valid_connection(flight1: Flight, flight2: Flight) -> bool:
    """Validate connection using UTC times with domestic/international rules"""
    if flight1.destination != flight2.origin:
        return False
    
    arr1_utc = to_utc_datetime(flight1.arrivalTime, flight1.destination)
    dep2_utc = to_utc_datetime(flight2.departureTime, flight2.origin)
    
    layover_minutes = int((dep2_utc - arr1_utc).total_seconds() / 60)
    
    connection_airport = flight1.destination
    if connection_airport not in airports:
        return False
        
    origin1_country = airports[flight1.origin].country if flight1.origin in airports else None
    origin2_country = airports[flight2.origin].country if flight2.origin in airports else None
    dest1_country = airports[flight1.destination].country if flight1.destination in airports else None
    dest2_country = airports[flight2.destination].country if flight2.destination in airports else None
    
    if not all([origin1_country, origin2_country, dest1_country, dest2_country]):
        return False
    
    is_domestic = (origin1_country == dest1_country == origin2_country == dest2_country)
    
    min_layover = 45 if is_domestic else 90
    max_layover = 360
    
    return min_layover <= layover_minutes <= max_layover

def find_connection_paths(origin: str, destination: str, date: str, max_stops: int = 2) -> List[List[Flight]]:
    """Find flight paths with connections using networkx"""
    valid_paths = []
    
    try:
        paths = list(nx.all_simple_paths(flight_graph, origin, destination, cutoff=max_stops + 1))
    except nx.NetworkXNoPath:
        return []
    
    # For each path, find valid flight combinations
    for path in paths:
        if len(path) < 2:  # Skip direct 
            continue
            
        # Get all possible flight combinations for this path
        path_flights = []
        for i in range(len(path) - 1):
            segment_flights = []
            origin_seg = path[i]
            dest_seg = path[i + 1]
            
            for flight in flights:
                if (flight.origin == origin_seg and 
                    flight.destination == dest_seg and
                    flight.departureTime.startswith(date)):
                    segment_flights.append(flight)
            
            path_flights.append(segment_flights)
        
        # Generate combinations and validate connections
        if all(path_flights): 
            valid_combinations = generate_flight_combinations(path_flights)
            valid_paths.extend(valid_combinations)
    
    return valid_paths

def generate_flight_combinations(path_flights: List[List[Flight]]) -> List[List[Flight]]:
    """Generate valid flight combinations for a path"""
    import itertools
    
    valid_combinations = []
    
    # Generate all combinations
    for combination in itertools.product(*path_flights):
        valid = True
        for i in range(len(combination) - 1):
            if not is_valid_connection(combination[i], combination[i + 1]):
                valid = False
                break
        
        if valid:
            valid_combinations.append(list(combination))
    
    # Early pruning
    return valid_combinations[:10]  # Max 10 combinations per path

def search_with_connections(origin: str, destination: str, date: str) -> List[Itinerary]:
    """Search including connections up to 2 stops"""
    results = []
    
    direct_results = search_direct_flights(origin, destination, date)
    results.extend(direct_results)
    
    connection_paths = find_connection_paths(origin, destination, date, max_stops=2)
    
    for path_flights in connection_paths:
        layovers = []
        total_price = sum(flight.price for flight in path_flights)
        total_duration = 0
        
        segments = []
        for i, flight in enumerate(path_flights):
            duration = calculate_duration(
                flight.departureTime, flight.origin,
                flight.arrivalTime, flight.destination
            )
            segments.append(FlightSegment(flight=flight, duration_minutes=duration))
            total_duration += duration
            
            if i < len(path_flights) - 1:
                next_flight = path_flights[i + 1]
                arr_utc = to_utc_datetime(flight.arrivalTime, flight.destination)
                dep_utc = to_utc_datetime(next_flight.departureTime, next_flight.origin)
                layover_min = int((dep_utc - arr_utc).total_seconds() / 60)
                
                layovers.append({
                    "airport": flight.destination,
                    "duration_minutes": layover_min
                })
                total_duration += layover_min
        
        itinerary = Itinerary(
            flights=segments,
            total_duration_minutes=total_duration,
            total_price=total_price,
            layovers=layovers
        )
        
        results.append(itinerary)
    
    results.sort(key=lambda x: x.total_duration_minutes)
    
    return results

def search_direct_flights(origin: str, destination: str, date: str) -> List[Itinerary]:
    """Search for direct flights only"""
    results = []
    
    for flight in flights:
        if flight.origin != origin or flight.destination != destination:
            continue
            
        flight_date = flight.departureTime[:10]
        if flight_date != date:
            continue
            
        duration = calculate_duration(
            flight.departureTime, flight.origin,
            flight.arrivalTime, flight.destination
        )
        
        segment = FlightSegment(flight=flight, duration_minutes=duration)
        
        itinerary = Itinerary(
            flights=[segment],
            total_duration_minutes=duration,
            total_price=flight.price,
            layovers=[]
        )
        
        results.append(itinerary)
    
    results.sort(key=lambda x: x.total_duration_minutes)
    
    return results

@app.on_event("startup")
async def startup_event():
    """Load flight data on startup"""
    load_flight_data()
    print(f"Loaded {len(airports)} airports and {len(flights)} flights")

@app.get("/")
async def root():
    return {"message": "SkyPath Flight Search API", "status": "running"}

@app.get("/airports")
async def get_airports():
    """Get all airports"""
    return list(airports.values())

@app.post("/search")
async def search_flights(request: SearchRequest) -> List[Itinerary]:
    """Search for flights"""
    
    request.origin = request.origin.upper().strip()
    request.destination = request.destination.upper().strip()
    
    if len(request.origin) != 3 or not request.origin.isalpha():
        raise HTTPException(status_code=400, detail="Origin must be a 3-letter IATA airport code")
    
    if len(request.destination) != 3 or not request.destination.isalpha():
        raise HTTPException(status_code=400, detail="Destination must be a 3-letter IATA airport code")
        
    if request.origin not in airports:
        raise HTTPException(status_code=400, detail=f"Invalid origin airport: {request.origin}")
    
    if request.destination not in airports:
        raise HTTPException(status_code=400, detail=f"Invalid destination airport: {request.destination}")
    
    if request.origin == request.destination:
        raise HTTPException(status_code=400, detail="Origin and destination cannot be the same")
    
    try:
        search_date = datetime.fromisoformat(request.date)
        today = date.today()
        min_date = date(2024, 1, 1)
        max_date = today + timedelta(days=365)
        
        if search_date.date() < min_date:
            raise HTTPException(status_code=400, detail="Search date cannot be before 2024")
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    results = search_with_connections(request.origin, request.destination, request.date)
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)