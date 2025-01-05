from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS
import google.generativeai as genai
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import threading
import time

# Initialize the Flask app
app = Flask(__name__)
load_dotenv()

# Load Hugging Face API token from environment variables
# api_token = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-pro')
cors = CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=os.getenv("SPOTIFY_CID"),
                            client_secret=os.getenv("SPOTIFY_SECRET"),
                            redirect_uri="http://example.com/",
                            scope="playlist-modify-public playlist-modify-private"))

playlists = {}
playlist_lock = threading.Lock()

def cleanup_playlists():
    """Background thread to delete playlists after 1 hour."""
    while True:
        time.sleep(60)  # Check every minute
        current_time = time.time()
        with playlist_lock:
            expired_playlists = [
                playlist_id for playlist_id, created_time in playlists.items()
                if current_time - created_time > 120  # 1 hour in seconds
            ]
            for playlist_id in expired_playlists:
                try:
                    sp.user_playlist_unfollow(sp.current_user()['id'], playlist_id)
                    print(f"Deleted playlist: {playlist_id}")
                    del playlists[playlist_id]
                except Exception as e:
                    print(f"Error deleting playlist {playlist_id}: {e}")

cleanup_thread = threading.Thread(target=cleanup_playlists, daemon=True)
cleanup_thread.start()
# Endpoint to generate a playlist
@app.route('/generate_playlist', methods=['POST'])
def generate_playlist():
    # Get the input data from the request
    data = request.json
    relationship_type = data.get('relationship_type', '')
    genres = data.get('genres', '')
    mood = data.get('mood', '')
    
    if not relationship_type or not genres or not mood:
        return jsonify({"error": "Please provide relationship_type, genres, and mood"}), 400
    
    # Generate a prompt for Hugging Face GPT-2 model
    prompt = f"Create a romantic playlist for a {relationship_type} couple who loves {genres} music. The mood should be {mood}. Provide a list of song titles and artists."
    
    try:
        # prompt= template_prompt.replace("<original_sentence>", sentence_original)
        response = model.generate_content(prompt, safety_settings=[
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}
        ])
        output = parse_playlist_to_correct_format(response.text)
        # print(output)
        song_list = fetch_songs_from_spotify(output)
    
    # Create a new playlist on Spotify
        user_id = sp.current_user()['id']
        playlist = sp.user_playlist_create(user=user_id, name="Romantic Playlist", public=True)
        playlist_id = playlist['id']

        # Add songs to the playlist
        sp.playlist_add_items(playlist_id, song_list)

        with playlist_lock:
            playlists[playlist_id] = time.time()

        return jsonify({
            "playlist_name": "Romantic Playlist",
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
    # song_title = "track:karta kya hai artist:karma"
    # print(song_titles)
    song_ids = []
    
    for title in song_titles:
        print(title)
        result = sp.search(q=title, limit=1)
        if result['tracks']['items']:
            print(result['tracks']['items'][0]['id'])
            song_ids.append(result['tracks']['items'][0]['id'])
    
    # print(song_ids)
    return song_ids

if __name__ == '__main__':
    app.run(debug=True)
