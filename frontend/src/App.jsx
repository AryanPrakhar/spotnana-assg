import { useState, useEffect } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [date, setDate] = useState('2024-03-15')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [airports, setAirports] = useState([])
  const [originSuggestions, setOriginSuggestions] = useState([])
  const [destinationSuggestions, setDestinationSuggestions] = useState([])
  const [showOriginDropdown, setShowOriginDropdown] = useState(false)
  const [showDestinationDropdown, setShowDestinationDropdown] = useState(false)

  useEffect(() => {
    fetchAirports()
  }, [])

  const fetchAirports = async () => {
    try {
      const response = await fetch(`${API_URL}/airports`)
      const data = await response.json()
      setAirports(data)
    } catch (err) {
      console.error('Failed to fetch airports:', err)
    }
  }

  const filterAirports = (searchText) => {
    if (!searchText || searchText.length < 1) return []
    const search = searchText.toLowerCase()
    return airports
      .filter(
        (airport) =>
          airport.code.toLowerCase().includes(search) ||
          airport.city.toLowerCase().includes(search) ||
          airport.name.toLowerCase().includes(search)
      )
      .slice(0, 8)
  }

  const handleOriginChange = (value) => {
    setOrigin(value)
    setOriginSuggestions(filterAirports(value))
    setShowOriginDropdown(value.length > 0)
  }

  const handleDestinationChange = (value) => {
    setDestination(value)
    setDestinationSuggestions(filterAirports(value))
    setShowDestinationDropdown(value.length > 0)
  }

  const selectOrigin = (airport) => {
    setOrigin(airport.code)
    setShowOriginDropdown(false)
  }

  const selectDestination = (airport) => {
    setDestination(airport.code)
    setShowDestinationDropdown(false)
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    setResults([])

    // Validation
    if (!origin || !destination) {
      setError('Please enter both origin and destination airports')
      setLoading(false)
      return
    }

    if (origin.length !== 3 || destination.length !== 3) {
      setError('Airport codes must be exactly 3 letters (e.g., JFK, LAX)')
      setLoading(false)
      return
    }

    if (origin.toUpperCase() === destination.toUpperCase()) {
      setError('Origin and destination must be different')
      setLoading(false)
      return
    }

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
      
      if (data.length === 0) {
        setError(`No flights found from ${origin.toUpperCase()} to ${destination.toUpperCase()} on ${date}. Try a different date or route.`)
      }
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
            <div className="form-group autocomplete-wrapper">
              <label htmlFor="origin">From</label>
              <input
                id="origin"
                type="text"
                placeholder="JFK or New York"
                value={origin}
                onChange={(e) => handleOriginChange(e.target.value)}
                onFocus={() => origin && setShowOriginDropdown(true)}
                onBlur={() => setTimeout(() => setShowOriginDropdown(false), 200)}
                required
                maxLength={3}
              />
              {showOriginDropdown && originSuggestions.length > 0 && (
                <div className="autocomplete-dropdown">
                  {originSuggestions.map((airport) => (
                    <div
                      key={airport.code}
                      className="autocomplete-item"
                      onClick={() => selectOrigin(airport)}
                    >
                      <strong>{airport.city} ({airport.code})</strong>
                      <div className="airport-name">{airport.name}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="form-group autocomplete-wrapper">
              <label htmlFor="destination">To</label>
              <input
                id="destination"
                type="text"
                placeholder="LAX or Los Angeles"
                value={destination}
                onChange={(e) => handleDestinationChange(e.target.value)}
                onFocus={() => destination && setShowDestinationDropdown(true)}
                onBlur={() => setTimeout(() => setShowDestinationDropdown(false), 200)}
                required
                maxLength={3}
              />
              {showDestinationDropdown && destinationSuggestions.length > 0 && (
                <div className="autocomplete-dropdown">
                  {destinationSuggestions.map((airport) => (
                    <div
                      key={airport.code}
                      className="autocomplete-item"
                      onClick={() => selectDestination(airport)}
                    >
                      <strong>{airport.city} ({airport.code})</strong>
                      <div className="airport-name">{airport.name}</div>
                    </div>
                  ))}
                </div>
              )}
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
            {error}
          </div>
        )}

        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Searching for the best flight connections...</p>
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