import streamlit as st
import requests

# --- PAGE CONFIG ---
st.set_page_config(page_title="SMT Expert System", page_icon="🔧")
st.title("🔧 SMT & Wave Expert")
st.markdown("Troubleshoot soldering defects using technical documentation.")

# --- INITIALIZE CHAT HISTORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- DISPLAY CHAT HISTORY ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- CHAT INPUT ---
if prompt := st.chat_input("Ask about a defect "):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- API CALL TO BACKEND ---
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # Connect to the /stream endpoint of your FastAPI backend
            # Note: 127.0.0.1:8000 is the default FastAPI address
            with requests.post(
                "http://127.0.0.1:8000/stream", 
                json={"input": prompt}, 
                stream=True
            ) as r:
                for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except requests.exceptions.ConnectionError:
            st.error("❌ Could not connect to the Backend. Is main.py running?")