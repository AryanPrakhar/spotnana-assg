from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from datetime import datetime
from typing import List, Optional
import os

app = FastAPI(title="SkyPath Flight Search API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
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

def load_flight_data():
    global airports, flights
    
    flights_file = "/app/flights.json"
    if not os.path.exists(flights_file):
        flights_file = "../flights.json"  # For local development
    
    with open(flights_file, 'r') as f:
        data = json.load(f)
        
    airports = {airport['code']: Airport(**airport) for airport in data['airports']}
    
    # Load flights
    flights = [Flight(**flight) for flight in data['flights']]

def calculate_duration(departure: str, arrival: str) -> int:
    """duration calculation without timezone"""
    dept = datetime.fromisoformat(departure)
    arr = datetime.fromisoformat(arrival)
    return int((arr - dept).total_seconds() / 60)

def search_direct_flights(origin: str, destination: str, date: str) -> List[Itinerary]:
    """Search for direct flights only"""
    results = []
    
    for flight in flights:
        if flight.origin != origin or flight.destination != destination:
            continue
            
        flight_date = flight.departureTime[:10]  # Extract YYYY-MM-DD
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
    
    # Search for direct flights only
    results = search_direct_flights(request.origin, request.destination, request.date)
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)