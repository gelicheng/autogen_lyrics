### File: core/spotify.py
import requests
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def get_spotify_token(client_id, client_secret):
    auth_url = "https://accounts.spotify.com/api/token"
    auth_response = requests.post(
        auth_url,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret)
    )
    if auth_response.status_code != 200:
        st.error(f"Failed to get Spotify token: {auth_response.text}")
        return None
    return auth_response.json().get("access_token")

def extract_playlist_id(playlist_url):
    return playlist_url.split("/")[-1].split("?")[0]

def get_playlist_tracks(access_token, playlist_id):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    tracks = []
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            tracks.extend(data["items"])
            url = data.get("next")
        return tracks
    except Exception as e:
        st.error(f"Error fetching playlist tracks: {e}")
        return []

def get_playlist_details(access_token, playlist_id):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching playlist details: {e}")
        return {}

def play_track(access_token, track_uri=None, device_id=None):
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {}

    if track_uri:
        payload["uris"] = [track_uri]

    params = {"device_id": device_id} if device_id else {}

    try:
        response = requests.put(
            "https://api.spotify.com/v1/me/player/play",
            headers=headers,
            json=payload,
            params=params
        )
        if response.status_code in [200, 204]:
            return "Playback started"
        else:
            return f"Failed to play: {response.text}"
    except Exception as e:
        return f"Playback error: {e}"


def pause_playback(access_token, device_id=None):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://api.spotify.com/v1/me/player/pause"
    if device_id:
        url += f"?device_id={device_id}"

    try:
        response = requests.put(url, headers=headers)
        if response.status_code in [200, 204]:
            return "⏸️ Playback paused"
        else:
            return f"Failed to pause: {response.text}"
    except Exception as e:
        return f"Pause error: {e}"


def next_track(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.post("https://api.spotify.com/v1/me/player/next", headers=headers)
        if response.status_code in [200, 204]:
            return "⏭️ Skipped to next track"
        else:
            return f"Failed to skip: {response.text}"
    except Exception as e:
        return f"Skip error: {e}"


def get_current_playback(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)
        if response.status_code == 200:
            data = response.json()
            item = data.get("item")
            if item:
                return f"🎵 Now playing: {item['name']} - {item['artists'][0]['name']}"
            else:
                return "Nothing is currently playing."
        else:
            return "No playback info available."
    except Exception as e:
        return f"Playback info error: {e}"

def search_tracks(access_token, query, limit=5, offset=0):
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "q": query,
        "type": "track",
        "limit": limit,
        "offset": offset
    }

    try:
        response = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)
        response.raise_for_status()
        results = response.json()["tracks"]["items"]
        return results  # list of track dicts
    except Exception as e:
        st.error(f"Search error: {e}")
        return []


def add_track_to_queue(access_token, track_uri, device_id=None):
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"uri": track_uri}
    if device_id:
        params["device_id"] = device_id

    try:
        response = requests.post("https://api.spotify.com/v1/me/player/queue", headers=headers, params=params)
        if response.status_code in [200, 204]:
            return "✅ Added to queue"
        else:
            return f"Failed to queue track: {response.text}"
    except Exception as e:
        return f"Queue error: {e}"

def get_playback_queue(access_token):
    headers = {"Authorization": f"Bearer " + access_token}
    try:
        response = requests.get("https://api.spotify.com/v1/me/player/queue", headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("queue", [])  # List of track objects
    except Exception as e:
        st.error(f"Error retrieving playback queue: {e}")
        return []

def create_playlist(access_token, user_id, name="My AI Playlist", description="Created by AI Assistant"):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "description": description,
        "public": False
    }
    try:
        response = requests.post(
            f"https://api.spotify.com/v1/users/{user_id}/playlists",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json().get("id")
    except Exception as e:
        st.error(f"Playlist creation error: {e}")
        return None

def add_track_to_playlist(access_token, playlist_id, track_uri):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "uris": [track_uri]
    }
    try:
        response = requests.post(
            f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
            headers=headers,
            json=payload
        )
        if response.status_code in [200, 201]:
            return "✅ Added to playlist"
        else:
            return f"Failed to add track: {response.text}"
    except Exception as e:
        return f"Error adding track: {e}"
    
def play_playlist(access_token: str, playlist_id: str):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        "context_uri": f"spotify:playlist:{playlist_id}"
    }
    response = requests.put(
        "https://api.spotify.com/v1/me/player/play",
        headers=headers,
        json=data
    )
    if response.status_code == 204:
        return "▶️ Playlist is now playing!"
    else:
        return f"⚠️ Failed to start playback: {response.text}"
