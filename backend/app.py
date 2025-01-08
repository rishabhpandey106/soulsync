from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from flask_cors import CORS
import google.generativeai as genai
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
from phi.agent import Agent
from phi.tools.googlesearch import GoogleSearch
from phi.model.google import Gemini
import threading
import time

app = Flask(__name__)
load_dotenv()
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

# Configure Google API and Spotify
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash-exp')
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CID"),
    client_secret=os.getenv("SPOTIFY_SECRET"),
    redirect_uri="http://example.com/",
    scope="playlist-modify-public playlist-modify-private"
))

playlists = {}
playlist_lock = threading.Lock()

def cleanup_playlists():
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
    data = request.json
    info = data.get('info', {})
    print(info)

    if not info:
        return jsonify({"error": "Please provide info"}), 400 
    
    try:
        webserach_agent = Agent(
            name="WebSearch Agent",
            role="Seach the web for information",
            model=Gemini(id="gemini-2.0-flash-exp"),
            tools=[GoogleSearch()],
            markdown=True,
            show_tool_calls=True,
            instructions=["Based on the information given by user, create a personalized playlist of songs. Suggest around 10-15 songs that are most relevant to this input. Include the song title and artist. Ensure the recommendations align closely with the information provided. If provided more than one artist name, mix playlist with given artist songs. Just give the song title and artist name in the response, in bullet points "]
        )

        output = webserach_agent.run(message=info)
        # print(output.content)

        song_pattern = r'["*]+\s*"(.+?)"\s*-\s*(.+)'
        songs = re.findall(song_pattern, output.content)
        cleaned_response = "\n".join([f"{title}  {artist}" for title, artist in songs])
        # output_songs = "\n".join([f"track:{song.split(' - ')[0]} artist:{song.split(' - ')[1]}" for song in cleaned_response.split("\n")])
        song_list = fetch_songs_from_spotify(cleaned_response)
        
        user_id = sp.current_user()['id']
        playlist_name = f"Generated Playlist"
        playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True)
        playlist_id = playlist['id']

        # Add songs to the playlist
        sp.playlist_add_items(playlist_id, song_list)

        with playlist_lock:
            playlists[playlist_id] = time.time()

        return jsonify({
            "playlist_name": playlist_name,
            "playlist_url": playlist['external_urls']['spotify']
        })
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500

def fetch_songs_from_spotify(playlist_description):
    # Split the Gemini response into song titles/artists
    song_titles = playlist_description.split("\n")
    song_ids = []
    
    for title in song_titles:
        print(title)
        result = sp.search(q=title, limit=1,type='track,album,episode')
        if result['tracks']['items']:
            print(result['tracks']['items'][0]['id'])
            song_ids.append(result['tracks']['items'][0]['id'])
    
    return song_ids

if __name__ == '__main__':
    app.run(debug=True)
