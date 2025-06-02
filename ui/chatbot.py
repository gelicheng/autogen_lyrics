import re
import streamlit as st
from core.autogen import setup_autogen_agents
from core.spotify import search_tracks, add_track_to_queue, add_track_to_playlist, create_playlist, play_playlist

def is_song_request(text):
    keywords = ["play", "queue", "add", "點歌", "放", "我想聽", "來一首"]
    # Avoid misinterpreting playlist operation commands as song requests
    playlist_keywords = ["playlist", "歌單", "播放清單", "加入歌單", "建立歌單"]
    return (
        any(k in text.lower() for k in keywords)
        and not any(p in text.lower() for p in playlist_keywords)
    )

def is_playlist_add_request(text):
    patterns = [
        r"create.*playlist", r"add.*playlist", r"建立.*歌單", r"加入.*歌單", r"播放清單"
    ]
    return any(re.search(p, text.lower()) for p in patterns)

def is_playlist_play_request(text):
    patterns = [
        r"play.*playlist", r"播放.*歌單", r"播.*歌單", r"播.*清單"
    ]
    return any(re.search(p, text.lower()) for p in patterns)

def render_pending_song_results():
    if st.session_state.get("pending_song_results"):
        for track in st.session_state["pending_song_results"]:
            title = track["name"]
            artist = ", ".join([a["name"] for a in track["artists"]])
            uri = track["uri"]
            offset = st.session_state.get("song_offset", 0)
            if st.button(f"🎵 Add to Queue: {title} - {artist}", key=f"queue-{uri}"):
                access_token = st.session_state.get("access_token")
                result = add_track_to_queue(access_token, uri)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"✅ Queued: {title} - {artist}\n{result}"
                })
                st.session_state["pending_song_results"] = None
                st.session_state["song_offset"] = 0
                st.rerun()
            
        if st.button("▶️ Show more", key=f"song-more-{offset}"):
            st.session_state["song_offset"] = offset + 10
            access_token = st.session_state.get("access_token")
            query = st.session_state.get("last_song_query") 
            if query and access_token:
                st.session_state["pending_song_results"] = search_tracks(access_token, query, limit=10, offset=st.session_state["song_offset"])
            st.rerun()

        if st.button("❌ None of these", key=f"song-none-{offset}"):
            st.session_state["pending_song_results"] = None
            st.session_state["song_offset"] = 0
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "Okay! You can enter a new song or artist to try again."
            })
            st.rerun()
        return True
    return False

def render_pending_playlist_results():
    if st.session_state.get("pending_playlist_results"):
        offset = st.session_state.get("playlist_offset", 0)

        for track in st.session_state["pending_playlist_results"]:
            title = track["name"]
            artist = ", ".join([a["name"] for a in track["artists"]])
            uri = track["uri"]
            if st.button(f"➕ Add to Playlist: {title} - {artist}", key=f"playlist-{uri}"):
                playlist_id = st.session_state.get("my_playlist_id")
                access_token = st.session_state.get("access_token")
                result = add_track_to_playlist(access_token, playlist_id, uri)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"{result}: {title} - {artist}"
                })
                st.session_state["pending_playlist_results"] = None
                st.session_state["playlist_offset"] = 0
                st.rerun()

        if st.button("▶️ Show more", key=f"playlist-more-{offset}"):
            st.session_state["playlist_offset"] = offset + 10
            access_token = st.session_state.get("access_token")
            query = st.session_state.get("last_playlist_query")
            if query and access_token:
                st.session_state["pending_playlist_results"] = search_tracks(access_token, query, limit=10, offset=st.session_state["playlist_offset"])
            st.rerun()

        if st.button("❌ None of these", key=f"playlist-none-{offset}"):
            st.session_state["pending_playlist_results"] = None
            st.session_state["playlist_offset"] = 0
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "Okay! You can enter a new song or artist to try again."
            })
            st.rerun()

        return True
    return False

def find_existing_playlist(sp, playlist_name):
    playlists = sp.current_user_playlists()
    for pl in playlists["items"]:
        if pl["name"] == playlist_name:
            return pl["id"]
    return None

def process_playlist_add_request(user_input):
    access_token = st.session_state.get("access_token")
    sp = st.session_state.get("spotify_client")
    if not access_token or not sp:
        return "⚠️ Please log in to Spotify first."

    if "my_playlist_id" not in st.session_state:
        existing_id = find_existing_playlist(sp, "AI Music Assistant Playlist")
        if existing_id:
            st.session_state["my_playlist_id"] = existing_id
            st.session_state.chat_history.append({"role": "assistant", "content": "✅ Found existing playlist. You can now add songs to it!"})
        else:
            user = sp.current_user()
            playlist_id = create_playlist(access_token, user["id"])
            if playlist_id:
                st.session_state["my_playlist_id"] = playlist_id
                st.session_state.chat_history.append({"role": "assistant", "content": "📝 Created a new playlist for you. Now tell me what songs you'd like to add!"})
            else:
                return "❌ Failed to create playlist."
    
    # Reset offset on new request
    if "playlist_offset" not in st.session_state:
        st.session_state["playlist_offset"] = 0
    st.session_state["last_playlist_query"] = user_input
    results = search_tracks(access_token, user_input, limit=10, offset=st.session_state["playlist_offset"])
    if results:
        st.session_state.pending_playlist_results = results
        st.session_state.chat_history.append({"role": "assistant", "content": "🎶 Select a song below to add to your playlist:"})
        st.rerun()
    return "❌ No results found for that request."

def process_song_request(user_input):
    if not st.session_state.get("is_premium", False):
        return "⚠️ Sorry, only Spotify Premium users can queue songs or control playback."
    access_token = st.session_state.get("access_token")
    if not access_token:
        return "⚠️ Please log in to Spotify first to queue a song."

    if "song_offset" not in st.session_state:
        st.session_state["song_offset"] = 0
    st.session_state["last_song_query"] = user_input
    results = search_tracks(access_token, user_input, limit=10, offset=st.session_state["song_offset"])
    if results:
        st.session_state.pending_song_results = results
        st.session_state.chat_history.append({"role": "assistant", "content": "🎶 Select a song below to add to your playlist:"})
        st.rerun()
    return "❌ No songs found for your request."

def music_chatbot_ui(agents, tracks_with_lyrics):
    st.header("🎵 Music Chatbot")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if render_pending_song_results():
        return
    if render_pending_playlist_results():
        return

    user_input = st.text_input("Ask me anything about your music, playlists, or moods:", key="music_chat_input")
    lyrics_input = " | ".join([f"{track['title']} by {track['artist']}" for track in tracks_with_lyrics[:5]])

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        if is_playlist_play_request(user_input):
            playlist_id = st.session_state.get("my_playlist_id")
            access_token = st.session_state.get("access_token")

            if not playlist_id:
                reply = "❌ You haven't created a playlist yet."
            elif not access_token:
                reply = "⚠️ Please log in to Spotify first."
            else:
                reply = play_playlist(access_token, playlist_id)
        elif is_playlist_add_request(user_input):
            reply = process_playlist_add_request(user_input)
        elif is_song_request(user_input):
            reply = process_song_request(user_input)
        else:
            context_messages = st.session_state.chat_history[-6:]
            prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in context_messages)
            system_message = (
                "You are a helpful and friendly music assistant chatbot. "
                "You can recommend music, generate lyrics based on user mood or ideas, "
                "analyze user playlists, and chat casually about music."
                f" Use the following song data for context: {lyrics_input}. "
                "If you don't know the answer, say 'I don't know' or ask for more details."
            )
            try:
                gemini_llm = agents["gemini_llm"]
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
                response_obj = gemini_llm.chat.completions.create(
                    model="gemini-2.0-flash-lite",
                    messages=messages
                )
                if response_obj and response_obj.choices:
                    reply = response_obj.choices[0].message.content
                else:
                    reply = "Sorry, I couldn't generate a response at this time."
            except Exception as e:
                reply = f"Error in chatbot: {str(e)}"

        st.session_state.chat_history.append({"role": "assistant", "content": reply})

    for msg in st.session_state.chat_history[-10:]:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**Bot:** {msg['content']}")