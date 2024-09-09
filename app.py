import os
from flask import Flask, render_template, request, redirect, session, url_for
import spotipy
import time
from spotipy.oauth2 import SpotifyOAuth
import requests
import json
import re

app = Flask(__name__)
app.secret_key = #random string
#app.config['SESSION_COOKIE_NAME'] = 'Spotify Login Session'




# Spotify API credentials
CLIENT_ID = #ENTER
CLIENT_SECRET = #ENTER
REDIRECT_URI = #ENTER


# Initialize Spotipy client
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=ENTER SCOPE
)



@app.route('/')
def login():
    session.clear()
    if os.path.exists(".cache"):
        os.remove(".cache")
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    print ("works")
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('stats'))


@app.route('/stats')
def stats():
    token_info = get_token()
    if not token_info:
        return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    results = sp.current_user_top_artists(limit=10, time_range='long_term')
    top_artists = results['items']

    track_results = sp.current_user_top_tracks(limit=10, time_range='long_term')
    top_tracks = track_results['items']
    

    
    return render_template('index.html', top_artists=top_artists, top_tracks=top_tracks)

@app.route('/switch-account')
def switch_account():
    print("Switching account...")
    session.clear()
    if os.path.exists(".cache"):
        os.remove(".cache")
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


def get_token():
    token_info = session.get('token_info', None)
    if not token_info:
        return None
    
    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60
    if is_expired:
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    
    return token_info



#WORKING ON IT
@app.route('/generate', methods=['POST'])
def generate():
    # Get the token and create a Spotify client
    token_info = get_token()
    if not token_info:
        return redirect('/')

    sp = spotipy.Spotify(auth=token_info['access_token'])
    top_artists_str = request.form.get('top_artists')
    top_tracks_str = request.form.get('top_tracks')

    # Check if the form data was received
    if not top_artists_str or not top_tracks_str:
        return "Error: Missing form data.", 400

    # Convert strings to lists
    top_artists = top_artists_str.split(', ')
    top_tracks = top_tracks_str.split(', ')
    # Get the user's prompt from the form
    user_prompt = request.form.get('user_prompt')

    gemini_prompt = (
        f"Top Artists:\n{top_artists}\n"
        f"Top Tracks:\n{top_tracks}\n"
        f"User Prompt:\n{user_prompt}"
    ) 
    headers = {
        'Content-Type': 'application/json',
    }


        

    completion = {
    "contents": [
        {
            "parts": [
                {"text": user_prompt+"\nGive a list of 15 songs such that the list is in this format: [Song1:Artist1 ; Song2:Artist2; ...]. An example output is [Love Story:Taylor Swift ; Shape of You: Ed Sheeran]."}
            ]
        }
    ],
    "systemInstruction": {
    "role": "system",
    "parts": [
      {
        "text": "Provide a list of songs in this format: [Song1:Artist1 ; Song2:Artist2; ...] without bolding, italicizing, or adding commentary."
      }
    ]
  },
    "safetySettings": [
        
    {
      "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
      "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    }
   ]
   }
    api_key = #ENTER GEMINI API KEY

# Set the request URL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
    response = requests.post(url, headers=headers, json=completion)
    response = response.json()
    print (response)
    response_content=response['candidates'][0]['content']['parts'][0]['text']
    match=re.search(r'\[.*?\]', response_content.strip())
    response_content=match.group(0) 
    # Parse the response to extract songs and artists
    song_artist_pairs = [pair.strip() for pair in response_content.split(';')]
    tracks_to_search = []
    for pair in song_artist_pairs:
        if ':' in pair:
            song, artist = pair.split(':')
            tracks_to_search.append((song.strip(), artist.strip()))
    
    # Search for tracks on Spotify
    track_uris = []
    for song, artist in tracks_to_search:
        search_query = f"track:{song} artist:{artist}"
        search_results = sp.search(q=search_query, type='track', limit=1)
        if search_results['tracks']['items']:
            track_uris.append(search_results['tracks']['items'][0]['uri'])
    
    # Get the current user's ID
    user_id = sp.current_user()['id']
    
    # Create a new playlist
    playlist_name = f"Custom Playlist"
    playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True)
    
    # Add tracks to the playlist
    if track_uris:
        sp.user_playlist_add_tracks(user=user_id, playlist_id=playlist['id'], tracks=track_uris)
    
    # Render the result page with the playlist link
    playlist_url = playlist['external_urls']['spotify']
    playlist_id = playlist['id']
    return render_template('index.html', playlist_url=playlist_url, playlist_name=playlist_name, playlist_id=playlist_id, top_artists=top_artists, top_tracks=top_tracks)




if __name__ == '__main__':
    app.run(debug=True)
