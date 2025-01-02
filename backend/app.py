from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from flask_cors import CORS
import google.generativeai as genai
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Initialize the Flask app
app = Flask(__name__)
load_dotenv()
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

# Configure Google API and Spotify
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-pro')
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CID"),
    client_secret=os.getenv("SPOTIFY_SECRET"),
    redirect_uri="http://example.com/",
    scope="playlist-modify-public playlist-modify-private"
))

# Endpoint to generate a playlist
@app.route('/generate_playlist', methods=['POST'])
def generate_playlist():
    # Get input data
    data = request.json
    user_type = data.get('user_type', 'listener')
    genres = data.get('genres', '')
    mood = data.get('mood', '')
    era = data.get('era', 'any time')
    energy = data.get('energy', 'any energy')
    favorite_artists = data.get('favorite_artists', [])
    occasion = data.get('occasion', 'general listening')
    language = data.get('language', 'any language')

    if not genres or not mood:
        return jsonify({"error": "Please provide genres and mood"}), 400

    prompt = (
        f"Create a playlist for a {user_type} "
        f"who enjoys {genres} music. The mood of the playlist should be {mood}. "
        f"Focus on songs from {era} with {energy} energy levels. "
        f"Include artists such as {', '.join(favorite_artists)} if possible. "
        f"The playlist is intended for {occasion}. Songs should be in {language}, "
        f"Always ensure the playlist must be same kind of music."
    )
    
    try:
        # Generate playlist using Google Gemini API
        response = model.generate_content(prompt, safety_settings=[
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}
        ])
        
        # Format the playlist response
        output = parse_playlist_to_correct_format(response.text)
        print(output)
        song_list = fetch_songs_from_spotify(output)
        
        # Create a playlist on Spotify
        user_id = sp.current_user()['id']
        playlist_name = f"{mood.capitalize()} {genres.capitalize()} Playlist"
        # playlist_name = f"Generated Playlist"
        playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True)
        playlist_id = playlist['id']

        # Add songs to the playlist
        sp.playlist_add_items(playlist_id, song_list)

        return jsonify({
            "playlist_name": playlist_name,
            "playlist_url": playlist['external_urls']['spotify']
        })
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500

def parse_playlist_to_correct_format(playlist_description):
    # Split the response into lines
    lines = playlist_description.split("\n")
    
    # Extract and clean the valid song entries
    formatted_songs = []
    for line in lines:
        line = line.strip()
        if line and ". " in line:  # Ensure it starts with "n. " format
            song_entry = line.split(". ", 1)[-1]  # Remove numbering
            song_entry = song_entry.strip("**").replace('"', '').strip('"')  # Clean unnecessary characters
            formatted_songs.append(song_entry)
    
    return "\n".join(formatted_songs)  # Join the cleaned list into a single string

def fetch_songs_from_spotify(playlist_description):
    # Split the Gemini response into song titles/artists
    song_titles = playlist_description.split("\n")
    song_ids = []
    
    for title in song_titles:
        print(title)
        result = sp.search(q=title, limit=1)
        if result['tracks']['items']:
            print(result['tracks']['items'][0]['id'])
            song_ids.append(result['tracks']['items'][0]['id'])
    
    return song_ids

if __name__ == '__main__':
    app.run(debug=True)
