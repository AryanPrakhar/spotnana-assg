import { useState } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [date, setDate] = useState('2024-03-15')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searched, setSearched] = useState(false)

  const handleSearch = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    setResults([])
    setSearched(true)

    try {
      const response = await fetch(`${API_URL}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          origin: origin.toUpperCase(),
          destination: destination.toUpperCase(),
          date,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Search failed')
      }

      const data = await response.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const formatDuration = (minutes) => {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}h ${mins}m`
  }

  return (
    <div className="app">
      <header className="header">
        <h1>✈️ SkyPath</h1>
        <p>Find your perfect flight connection</p>
      </header>

      <main className="main">
        <form className="search-form" onSubmit={handleSearch}>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="origin">From</label>
              <input
                id="origin"
                type="text"
                placeholder="JFK"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                required
                maxLength={3}
              />
            </div>

            <div className="form-group">
              <label htmlFor="destination">To</label>
              <input
                id="destination"
                type="text"
                placeholder="LAX"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                required
                maxLength={3}
              />
            </div>

            <div className="form-group">
              <label htmlFor="date">Date</label>
              <input
                id="date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="search-button" disabled={loading}>
              {loading ? 'Searching...' : 'Search Flights'}
            </button>
          </div>
        </form>

        {error && (
          <div className="error-message">
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading && <div className="loading">Searching for flights...</div>}

        {!loading && results.length === 0 && origin && destination && !error && searched && (
          <div className="no-results">
            No flights found for {origin} → {destination} on {date}
          </div>
        )}

        {results.length > 0 && (
          <div className="results">
            <h2>Found {results.length} itineraries</h2>
            {results.map((itinerary, idx) => (
              <div key={idx} className="itinerary-card">
                <div className="itinerary-header">
                  <div className="itinerary-summary">
                    <span className="stops">
                      {itinerary.flights.length === 1
                        ? 'Direct'
                        : `${itinerary.flights.length - 1} stop${
                            itinerary.flights.length > 2 ? 's' : ''
                          }`}
                    </span>
                    <span className="duration">
                      {formatDuration(itinerary.total_duration_minutes)}
                    </span>
                    <span className="price">${itinerary.total_price.toFixed(2)}</span>
                  </div>
                </div>

                <div className="flights">
                  {itinerary.flights.map((segment, segIdx) => (
                    <div key={segIdx}>
                      <div className="flight-segment">
                        <div className="flight-info">
                          <div className="flight-number">
                            {segment.flight.airline} {segment.flight.flightNumber}
                          </div>
                          <div className="flight-aircraft">{segment.flight.aircraft}</div>
                        </div>
                        <div className="flight-route">
                          <div className="airport">
                            <div className="airport-code">{segment.flight.origin}</div>
                            <div className="time">
                              {new Date(segment.flight.departureTime).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </div>
                          </div>
                          <div className="flight-line">
                            <div className="duration-badge">
                              {formatDuration(segment.duration_minutes)}
                            </div>
                          </div>
                          <div className="airport">
                            <div className="airport-code">{segment.flight.destination}</div>
                            <div className="time">
                              {new Date(segment.flight.arrivalTime).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </div>
                          </div>
                        </div>
                      </div>

                      {segIdx < itinerary.flights.length - 1 && (
                        <div className="layover">
                          <div className="layover-icon">⏱</div>
                          <div className="layover-info">
                            Layover in {itinerary.layovers[segIdx].airport}:{' '}
                            {formatDuration(itinerary.layovers[segIdx].duration_minutes)}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <footer className="footer">
        <p>SkyPath Flight Search Engine</p>
      </footer>
    </div>
  )
}

export default App