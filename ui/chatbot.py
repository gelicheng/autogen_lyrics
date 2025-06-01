import streamlit as st
from core.autogen import setup_autogen_agents
from core.spotify import search_tracks, add_track_to_queue

def is_song_request(text):
    keywords = ["play", "queue", "add", "點歌", "放", "我想聽", "來一首"]
    return any(kw in text.lower() for kw in keywords)

# Music chatbot UI and logic
def music_chatbot_ui(agents, tracks_with_lyrics):
    st.header("🎵 Music Chatbot")

    if "pending_song_results" not in st.session_state:
        st.session_state.pending_song_results = None

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_input = st.text_input("Ask me anything about your music, playlists, or moods:", key="music_chat_input")
    lyrics_input = " | ".join([f"{track['title']} by {track['artist']}" for track in tracks_with_lyrics[:5]])

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Check whether it is a song request (not via Gemini)
        if st.session_state.pending_song_results:
            for track in st.session_state.pending_song_results:
                title = track["name"]
                artist = ", ".join([a["name"] for a in track["artists"]])
                uri = track["uri"]
                if st.button(f"🎵 Add: {title} - {artist}", key=uri):
                    access_token = st.session_state.get("access_token")
                    result = add_track_to_queue(access_token, uri)
                    st.session_state.chat_history.append({"role": "assistant", "content": f"✅ Queued: {title} - {artist}\n{result}"})
                    st.session_state.pending_song_results = None
                    st.rerun()
        elif is_song_request(user_input):
            # Block non-premium users from entering queue logic
            if not st.session_state.get("is_premium", False):
                reply = "⚠️ Sorry, only Spotify Premium users can queue songs or control playback."
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                return
            access_token = st.session_state.get("access_token")
            if not access_token:
                reply = "⚠️ Please log in to Spotify first to queue a song."
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
            else:
                results = search_tracks(access_token, user_input, limit=5)
                if results:
                    st.session_state.pending_song_results = results
                    reply = "🎶 Please select the song you'd like to queue:"
                else:
                    reply = "❌ No songs found for your request."
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
        else:
            # Pass all other messages to Gemini for processing.
            # Compose prompt from last few messages for context
            context_messages = st.session_state.chat_history[-6:]
            prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in context_messages)

            system_message = (
                "You are a helpful and friendly music assistant chatbot. "
                "You can recommend music, generate lyrics based on user mood or ideas, "
                "analyze user playlists, and chat casually about music."
                f' Use the following song data for context: {lyrics_input}. '
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

    # Display chat history
    for msg in st.session_state.chat_history[-10:]:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**Bot:** {msg['content']}")