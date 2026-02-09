from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from datetime import datetime
from typing import List, Optional
import os
import networkx as nx

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
        flights_file = "../flights.json"  # For local development
    
    with open(flights_file, 'r') as f:
        data = json.load(f)
        
    airports = {airport['code']: Airport(**airport) for airport in data['airports']}
    
    # Load flights
    flights = [Flight(**flight) for flight in data['flights']]
    
    # Build flight graph for connection search
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

def calculate_duration(departure: str, arrival: str) -> int:
    dept = datetime.fromisoformat(departure)
    arr = datetime.fromisoformat(arrival)
    return int((arr - dept).total_seconds() / 60)

def is_valid_connection(flight1: Flight, flight2: Flight) -> bool:
    arr1 = datetime.fromisoformat(flight1.arrivalTime)
    dep2 = datetime.fromisoformat(flight2.departureTime)
    
    # check: arrival before departure with some buffer
    layover_minutes = int((dep2 - arr1).total_seconds() / 60)
    return 30 <= layover_minutes <= 360  # 30min to 6hrs layover

def find_connection_paths(origin: str, destination: str, date: str, max_stops: int = 2) -> List[List[Flight]]:
    """Find flight paths with connections using networkx"""
    valid_paths = []
    
    # Find all simple paths up to max_stops + 1 length
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
            duration = calculate_duration(flight.departureTime, flight.arrivalTime)
            segments.append(FlightSegment(flight=flight, duration_minutes=duration))
            total_duration += duration
            
            if i < len(path_flights) - 1:
                next_flight = path_flights[i + 1]
                arr_time = datetime.fromisoformat(flight.arrivalTime)
                dep_time = datetime.fromisoformat(next_flight.departureTime)
                layover_min = int((dep_time - arr_time).total_seconds() / 60)
                
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
            
        duration = calculate_duration(flight.departureTime, flight.arrivalTime)
        
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
    
    # Validate airports
    if request.origin not in airports:
        raise HTTPException(status_code=400, detail=f"Invalid origin airport: {request.origin}")
    
    if request.destination not in airports:
        raise HTTPException(status_code=400, detail=f"Invalid destination airport: {request.destination}")
    
    if request.origin == request.destination:
        raise HTTPException(status_code=400, detail="Origin and destination cannot be the same")
    
    # Validate date format
    try:
        datetime.fromisoformat(request.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    results = search_with_connections(request.origin, request.destination, request.date)
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)