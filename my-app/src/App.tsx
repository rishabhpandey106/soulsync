import { useState } from 'react';
import './App.css';

function App() {
  const [userInput, setUserInput] = useState(""); // Single input for user expression
  const [playlistLink, setPlaylistLink] = useState("");
  const [loading, setLoading] = useState(false);

  const generatePlaylist = async () => {
    setLoading(true);
    const response = await fetch("http://127.0.0.1:5000/generate_playlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        info: userInput
      })
    });
    const data = await response.json();
    setPlaylistLink(data.playlist_url);
    setLoading(false);
  };

  return (
    <div>
      <a href="https://github.com/rishabhpandey106/soulsync"><h1>SoulSyn&copy;</h1></a>
      <p>Tell us what you're feeling, what you love, or the kind of songs you want, and we'll create a personalized playlist just for you!</p>
      <section className="user-input-section">
        <textarea
          className="user-input"
          placeholder="Express yourself (e.g., 'I want songs that make me feel energized and inspired' or 'I'm in love and need a romantic playlist')"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
        />
        <button onClick={generatePlaylist} disabled={loading || !userInput.trim()} className='btn'>
          {loading ? "Generating..." : "Generate Playlist"}
        </button>
      </section>

      {loading && (
        <div className="skeleton-loader">
          <a href="#" className="skeleton skeleton-button">Loading</a>
        </div>
      )}

      {playlistLink && !loading && (
        <div className="playlist-link">
          <h3>Your Playlist:</h3>
          <a href={playlistLink} target="_blank" rel="noopener noreferrer">Click here to open your personalized playlist</a>
        </div>
      )}
    </div>
  );
}

export default App;
