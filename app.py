import streamlit as st
from agent import ask_agent

st.set_page_config(page_title="Skylark Drones — BI Agent", page_icon="📊")
st.title("📊 Skylark Drones — BI Agent")
st.caption("Ask about your deals pipeline or work orders — live from monday.com")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # for Gemini's chat memory
if "messages" not in st.session_state:
    st.session_state.messages = []  # for displaying in the UI

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("e.g. How's our pipeline looking for the energy sector this quarter?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking monday.com..."):
            try:
                answer = ask_agent(prompt)
            except Exception as e:
                answer = f"Something went wrong reaching the data or the model: {e}"
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})