import { useState } from 'react'
import './App.css'

function App() {
  const [relationshipType, setRelationshipType] = useState("");
  const [genres, setGenres] = useState("");
  const [mood, setMood] = useState("");
  const [playlistLink, setPlaylistLink] = useState("");
  const [loading, setLoading] = useState(false);

  const generatePlaylist = async () => {
    setLoading(true);
    const response = await fetch("http://127.0.0.1:5000/generate_playlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        relationship_type: relationshipType,
        genres: genres,
        mood: mood
      })
    });
    const data = await response.json();
    setPlaylistLink(data.playlist_url);
    setLoading(false);
  };

  return (
    <div>
      <h1>AI Romantic Playlist Generator</h1>
      <input
        className="relationship-type-input"
        type="text"
        placeholder="Relationship Type (e.g., Long-distance)"
        value={relationshipType}
        onChange={(e) => setRelationshipType(e.target.value)}
      />
      <input
        className="genres-input"
        type="text"
        placeholder="Genres (e.g., Pop, Acoustic)"
        value={genres}
        onChange={(e) => setGenres(e.target.value)}
      />
      <input
        className="mood-input"
        type="text"
        placeholder="Mood (e.g., Chill, Romantic)"
        value={mood}
        onChange={(e) => setMood(e.target.value)}
      />
      <button onClick={generatePlaylist}>Generate Playlist</button>

      {loading && (
        <div className="skeleton-loader">
          {/* <h3 className="skeleton skeleton-text">............</h3> */}
          <a href='#' className="skeleton skeleton-button">Loading</a>
        </div>
      )}

      {playlistLink && !loading && (
        <div className="playlist-link">
          <h3>Your Playlist:</h3>
          <a href={playlistLink} target="_blank" rel="noopener noreferrer">Click here to open your romantic playlist</a>
        </div>
      )}
    </div>
  );
}

export default App;
