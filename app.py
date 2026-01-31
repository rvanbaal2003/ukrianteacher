import os
import streamlit as st
from openai import OpenAI
import base64
import difflib
from datetime import datetime
import tempfile
from streamlit_mic_recorder import mic_recorder

def get_pronunciation_feedback(target_text: str, spoken_text: str, client: OpenAI) -> dict:
    """Gebruik AI om uitspraak te evalueren"""
    similarity = difflib.SequenceMatcher(None, target_text.lower(), spoken_text.lower()).ratio()
    
    feedback_prompt = f"""
Je bent een Oekraïense uitspraakdocent. Een student moest dit zeggen:
"{target_text}"

De student zei dit (getranscribeerd):
"{spoken_text}"

Geef vriendelijke, constructieve feedback in het Nederlands:
1. Een score van 1-10
2. Wat ging er goed
3. Wat kan beter (specifieke klanken/woorden)
4. Een tip voor verbetering

Houd het kort en bemoedigend!
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": feedback_prompt}],
            temperature=0.7,
            max_tokens=300
        )
        feedback_text = response.choices[0].message.content
    except:
        feedback_text = "Kon geen feedback genereren."
    
    return {
        "similarity": similarity,
        "feedback": feedback_text,
        "target": target_text,
        "spoken": spoken_text
    }


def render_teacher_output(text: str, client: OpenAI, show_audio=True, speech_speed=1.0):
    """Render output netjes met audio playback en snelheidscontrole"""
    import re

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    if len(lines) <= 1:
        pattern = r"(?=(?:UA\s*\(uitspraak\)|UA|NL|Correctie|Uitleg)\s*:)"
        chunks = re.split(pattern, text)
        lines = [c.strip() for c in chunks if c.strip()]

    parts = {}
    for line in lines:
        if ":" in line:
            k, v = line.split(":", 1)
            parts[k.strip()] = v.strip()

    if not parts:
        st.markdown(text)
        return parts

    st.markdown("### 🇺🇦 Oekraïens")
    ukrainian_text = parts.get("UA", "")
    if ukrainian_text and show_audio:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(ukrainian_text)
        with col2:
            if st.button("🔊", key=f"speak_{hash(ukrainian_text)}", use_container_width=True):
                try:
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=ukrainian_text,
                        speed=speech_speed
                    )
                    
                    audio_bytes = response.content
                    audio_b64 = base64.b64encode(audio_bytes).decode()
                    audio_html = f"""
                        <audio autoplay>
                            <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
                        </audio>
                    """
                    st.markdown(audio_html, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Audio fout: {e}")
    elif ukrainian_text:
        st.write(ukrainian_text)

    st.markdown("### 🔤 Uitspraak")
    st.write(parts.get("UA (uitspraak)", ""))

    st.markdown("### 🇳🇱 Nederlands")
    st.write(parts.get("NL", ""))

    if parts.get("Correctie"):
        st.markdown("### ✅ Correctie")
        st.write(parts.get("Correctie", ""))

    if parts.get("Uitleg"):
        st.markdown("### 💡 Uitleg")
        st.write(parts.get("Uitleg", ""))
    
    return parts


st.set_page_config(
    page_title="🇺🇦 Oekraïense Uitspraak Trainer", 
    page_icon="🇺🇦",
    layout="wide"
)

st.title("🇺🇦 Oekraïense Uitspraak Trainer")
st.caption("Leer perfect Oekraïens uitspreken met AI-feedback")

# Try Streamlit secrets first, then environment variable
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("⚠️ Geen OPENAI_API_KEY gevonden. Zet die in Streamlit secrets of als environment variable.")
    st.stop()

client = OpenAI(api_key=api_key)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_practice" not in st.session_state:
    st.session_state.current_practice = None
if "practice_history" not in st.session_state:
    st.session_state.practice_history = []

# Sidebar
with st.sidebar:
    st.header("⚙️ Instellingen")
    level = st.selectbox("Niveau", ["A1", "A2", "B1", "B2"], index=0)
    
    st.divider()
    
    # SNELHEIDSCONTROLE
    st.markdown("### 🎚️ Uitspraak Snelheid")
    speech_speed = st.slider(
        "Spreeksnelheid",
        min_value=0.5,
        max_value=1.5,
        value=1.0,
        step=0.1,
        help="0.5 = heel langzaam, 1.0 = normaal, 1.5 = snel"
    )
    if speech_speed < 0.8:
        st.info("🐢 Langzaam - perfect voor beginners")
    elif speech_speed > 1.2:
        st.info("🐰 Snel - voor gevorderden")
    
    st.divider()
    
    mode = st.radio(
        "Kies modus:",
        ["🎯 Uitspraak Oefenen", "💬 Conversatie"],
        index=0
    )
    
    st.divider()
    
    # Progress
    if mode == "🎯 Uitspraak Oefenen" and st.session_state.practice_history:
        st.markdown("### 📊 Jouw Voortgang")
        
        total = len(st.session_state.practice_history)
        avg_score = sum(h['score'] for h in st.session_state.practice_history) / total if total > 0 else 0
        
        st.metric("Geoefende zinnen", total)
        st.metric("Gemiddelde score", f"{int(avg_score)}%")
        
        if total > 0:
            st.markdown("**Laatste pogingen:**")
            for hist in reversed(st.session_state.practice_history[-5:]):
                emoji = "🌟" if hist['score'] >= 90 else "👍" if hist['score'] >= 70 else "💪"
                st.write(f"{emoji} {hist['score']}% - {hist['timestamp']}")
        
        if st.button("🔄 Reset Voortgang"):
            st.session_state.practice_history = []
            st.rerun()
    
    st.divider()
    st.markdown("### 📚 Tips")
    if mode == "🎯 Uitspraak Oefenen":
        st.markdown("""
        - 🔊 Klik speaker voor uitspraak
        - 🎚️ Pas snelheid aan hierboven
        - 🎤 Klik microfoon en spreek in
        - 🔄 Je kunt oneindig proberen
        """)

# UITSPRAAK OEFENMODUS
if mode == "🎯 Uitspraak Oefenen":
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📝 Kies een Oefenzin")
        
        # TAB SELECTIE: Genereren of Eigen Zin
        tab1, tab2 = st.tabs(["🎲 Genereer zin", "✍️ Eigen zin"])
        
        with tab1:
            topic = st.text_input(
                "Onderwerp",
                placeholder="bijv: groeten, restaurant, winkelen",
                help="Waar wil je over leren?",
                key="topic_input"
            )
            
            if st.button("🎲 Nieuwe zin genereren", type="primary", use_container_width=True):
                with st.spinner("Nieuwe zin maken..."):
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{
                                "role": "user", 
                                "content": f"""Geef 1 nuttige Oekraïense zin over '{topic or 'dagelijks leven'}' 
                                voor niveau {level}. Format op aparte regels:

UA: <Oekraïense zin>
UA (uitspraak): <transliteratie>
NL: <Nederlandse vertaling>
Correctie: Geen fouten.
Uitleg: <korte context>"""
                            }],
                            temperature=0.8,
                            max_tokens=200
                        )
                        
                        practice_text = response.choices[0].message.content
                        st.session_state.current_practice = practice_text
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Fout: {e}")
        
        with tab2:
            st.info("💡 Typ hieronder een Oekraïense zin die je wilt oefenen")
            
            custom_sentence = st.text_area(
                "Oekraïense zin",
                placeholder="Доброго ранку!",
                help="Typ de Oekraïense zin die je wilt oefenen",
                key="custom_sentence",
                height=100
            )
            
            if st.button("✅ Gebruik deze zin", type="primary", use_container_width=True):
                if custom_sentence.strip():
                    with st.spinner("Zin verwerken..."):
                        try:
                            # Vraag AI om uitleg bij deze zin
                            response = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[{
                                    "role": "user", 
                                    "content": f"""Deze Oekraïense zin moet geoefend worden: "{custom_sentence}"

Geef de volgende informatie op aparte regels:

UA: {custom_sentence}
UA (uitspraak): <transliteratie in Latijnse letters>
NL: <Nederlandse vertaling>
Correctie: Geen fouten.
Uitleg: <korte context wanneer je deze zin gebruikt>"""
                                }],
                                temperature=0.5,
                                max_tokens=200
                            )
                            
                            practice_text = response.choices[0].message.content
                            st.session_state.current_practice = practice_text
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Fout: {e}")
                else:
                    st.warning("⚠️ Vul eerst een zin in!")
    
    with col2:
        st.markdown("### 🎯 Huidige Oefenzin")
        if st.session_state.current_practice:
            parts = render_teacher_output(
                st.session_state.current_practice, 
                client, 
                show_audio=True,
                speech_speed=speech_speed
            )
            ukrainian_text = parts.get("UA", "") if parts else ""
            
            st.markdown("---")
            st.markdown("### 🎤 Spreek de zin in")
            
            # MIC RECORDER
            audio_bytes = mic_recorder(
                start_prompt="🎤 Klik om op te nemen",
                stop_prompt="⏹️ Stop opname",
                just_once=False,
                use_container_width=True,
                key='recorder'
            )
            
            if audio_bytes:
                st.audio(audio_bytes['bytes'])
                
                if st.button("✅ Evalueer mijn uitspraak", type="primary", use_container_width=True):
                    with st.spinner("🎧 Luisteren..."):
                        try:
                            # Save audio to temp file
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                                tmp_file.write(audio_bytes['bytes'])
                                tmp_path = tmp_file.name
                            
                            # Transcribe
                            with open(tmp_path, 'rb') as audio_file:
                                transcript = client.audio.transcriptions.create(
                                    model="whisper-1",
                                    file=audio_file,
                                    language="uk"
                                )
                            
                            # Cleanup
                            os.unlink(tmp_path)
                            
                            spoken_text = transcript.text
                            
                            st.markdown("### 📊 Resultaat")
                            st.markdown(f"**Jij zei:** {spoken_text}")
                            st.markdown(f"**Doel:** {ukrainian_text}")
                            
                            feedback = get_pronunciation_feedback(
                                ukrainian_text, 
                                spoken_text, 
                                client
                            )
                            
                            score_pct = int(feedback["similarity"] * 100)
                            
                            # Save history
                            st.session_state.practice_history.append({
                                'score': score_pct,
                                'target': ukrainian_text,
                                'spoken': spoken_text,
                                'timestamp': datetime.now().strftime("%H:%M")
                            })
                            
                            # Show score
                            if score_pct >= 90:
                                st.success(f"🌟 Uitstekend! {score_pct}%")
                                st.balloons()
                            elif score_pct >= 70:
                                st.warning(f"👍 Goed bezig! {score_pct}%")
                            else:
                                st.error(f"💪 Blijf oefenen! {score_pct}%")
                            
                            st.progress(feedback["similarity"])
                            
                            st.markdown("#### 💬 Docent Feedback:")
                            st.markdown(feedback["feedback"])
                            
                            if score_pct < 90:
                                st.info("💡 Luister opnieuw en probeer nog eens!")
                            
                        except Exception as e:
                            st.error(f"Fout: {str(e)}")
        else:
            st.info("👈 Genereer een zin of voer je eigen zin in om te beginnen!")

# CONVERSATIE MODUS
else:
    st.markdown("---")
    
    # Chat history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                render_teacher_output(msg["content"], client, show_audio=True, speech_speed=speech_speed)

    # Mic input voor conversatie
    st.markdown("### 🎤 Spreek je vraag in")
    conv_audio = mic_recorder(
        start_prompt="🎤 Klik om vraag in te spreken",
        stop_prompt="⏹️ Stop opname",
        just_once=False,
        use_container_width=True,
        key='conv_recorder'
    )
    
    if conv_audio and st.button("Transcribeer en verstuur"):
        with st.spinner("Transcriberen..."):
            try:
                # Save and transcribe
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                    tmp_file.write(conv_audio['bytes'])
                    tmp_path = tmp_file.name
                
                with open(tmp_path, 'rb') as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                
                os.unlink(tmp_path)
                
                transcribed = transcript.text
                st.success(f"📝 '{transcribed}'")
                
                st.session_state.messages.append({"role": "user", "content": transcribed})
                
                with st.spinner("Antwoord maken..."):
                    SYSTEM = f"""Oekraïense taaldocent. Format op aparte regels:
UA: <Oekraïens>
UA (uitspraak): <transliteratie>
NL: <Nederlands>
Correctie: <correctie of 'Geen fouten.'>
Uitleg: <korte uitleg>
Niveau: {level}"""
                    
                    api_messages = [{"role": "system", "content": SYSTEM}]
                    api_messages.extend(st.session_state.messages)
                    
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=api_messages,
                        temperature=0.7,
                        max_tokens=500
                    )
                    
                    answer = response.choices[0].message.content
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Fout: {str(e)}")

    # Text input
    prompt = st.chat_input("Of typ hier...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("Antwoord maken..."):
            SYSTEM = f"""Oekraïense taaldocent. Format op aparte regels:
UA: <Oekraïens>
UA (uitspraak): <transliteratie>
NL: <Nederlands>
Correctie: <correctie of 'Geen fouten.'>
Uitleg: <korte uitleg>
Niveau: {level}"""
            
            api_messages = [{"role": "system", "content": SYSTEM}]
            api_messages.extend(st.session_state.messages)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=api_messages,
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()
