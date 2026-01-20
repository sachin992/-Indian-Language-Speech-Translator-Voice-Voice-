

import streamlit as st
import os
import tempfile
from streamlit_mic_recorder import mic_recorder
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- OpenAI Client Setup ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.sidebar.error("❌ OPENAI_API_KEY not found!")
    st.stop()

client = OpenAI(api_key=api_key)

# --- Session State ---
for key in ["audio_file_path", "transcript", "translated_text", "audio_output"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "transcript" and key != "translated_text" else ""

# --- Updated: Top 22 Indian Scheduled Languages ---
# These codes (ISO 639-1) are compatible with OpenAI Whisper and GPT models.
languages = {
    "Hindi": "hi",
    "Bengali": "bn",
    "Marathi": "mr",
    "Telugu": "te",
    "Tamil": "ta",
    "Gujarati": "gu",
    "Urdu": "ur",
    "Kannada": "kn",
    "Odia": "or",
    "Malayalam": "ml",
    "Punjabi": "pa",
    "Assamese": "as",
    "Maithili": "mai",
    "Santali": "sat",  # Note: Limited TTS support for smaller dialects
    "Kashmiri": "ks",
    "Nepali": "ne",
    "Konkani": "kok",
    "Sindhi": "sd",
    "Dogri": "doi",
    "Manipuri": "mni",
    "Bodo": "brx",
    "Sanskrit": "sa",
    "English": "en"
}

st.sidebar.header("⚙️ Translation Settings")
source_lang = st.sidebar.selectbox("Source Language", list(languages.keys()), index=0) # Hindi default
target_lang = st.sidebar.selectbox("Target Language", list(languages.keys()), index=12) # Maithili default

# --- UI Layout ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📢 Input Audio")
    input_tab1, input_tab2 = st.tabs(["🎤 Record", "📁 Upload"])

    with input_tab1:
        audio_record = mic_recorder(
            start_prompt="🎙️ Start Recording",
            stop_prompt="🛑 Stop Recording",
            key='recorder'
        )
        if audio_record:
            st.audio(audio_record['bytes'])
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio_record['bytes'])
                st.session_state.audio_file_path = f.name

    with input_tab2:
        uploaded_file = st.file_uploader("Upload audio", type=["wav", "mp3"])
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(uploaded_file.getbuffer())
                st.session_state.audio_file_path = f.name
            st.audio(uploaded_file)

    if st.session_state.audio_file_path and st.button("🔄 Transcribe & Translate"):
        try:
            # 1. Transcription (Whisper)
            with st.spinner(f"Transcribing {source_lang}..."):
                with open(st.session_state.audio_file_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="hi" # Use the code
                    )
                st.session_state.transcript = transcription.text

            # 2. Translation (LLM)
            with st.spinner(f"Translating to {target_lang}..."):
                prompt = ChatPromptTemplate.from_template(
                    "You are a professional translator. Translate this from {source} to {target}.\n"
                    "Script: Use the native script of the {target} language.\n"
                    "Context: Use natural, conversational tones.\n"
                    "Return ONLY the translated text.\n\n{text}"
                )
                llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
                chain = prompt | llm
                result = chain.invoke({
                    "source": source_lang, 
                    "target": target_lang, 
                    "text": st.session_state.transcript
                })
                st.session_state.translated_text = result.content.strip()

            # 3. Text-to-Speech
            with st.spinner("Generating Audio..."):
                speech = client.audio.speech.create(
                    model="tts-1", 
                    voice="alloy",
                    input=st.session_state.translated_text
                )
                st.session_state.audio_output = speech.read()

        except Exception as e:
            st.error(f"Error: {str(e)}")

with col2:
    st.subheader("🎵 Output")
    if st.session_state.transcript:
        st.write(f"**Original ({source_lang})**")
        st.info(st.session_state.transcript)

    if st.session_state.translated_text:
        st.write(f"**Translated ({target_lang})**")
        st.success(st.session_state.translated_text)

    if st.session_state.audio_output:
        st.audio(st.session_state.audio_output, format="audio/mp3")
        st.download_button("📥 Download", st.session_state.audio_output, "output.mp3", "audio/mp3")

st.caption("🤖 Powered by OpenAI & LangChain")