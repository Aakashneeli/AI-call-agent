import os
import json
import base64
import asyncio
import websockets
import audioop
import wave
import time
import requests
import subprocess
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from dotenv import load_dotenv
from groq import Groq
from utils import pcm_to_mulaw, mulaw_to_pcm
from rag import init_knowledge_base, get_knowledge_base

# Fix for Windows asyncio subprocess issue (Must be before app startup)
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
MY_PHONE_NUMBER = os.getenv("MY_PHONE_NUMBER")

# Initialize Knowledge Base
DATA_DIR = os.path.join(os.getcwd(), "data")
# We'll initialize it lazily or on startup. Let's do it globally for simplicity in this prototype.
# Note: This might block startup slightly, but it's fine for a prototype.
print("Initializing Knowledge Base...")
init_knowledge_base(DATA_DIR)
print("Knowledge Base Initialized.")

if not GROQ_API_KEY:
    print("Error: GROQ_API_KEY not found.")

app = FastAPI()
client = Groq(api_key=GROQ_API_KEY)
from vad import VoiceActivityDetector

# Initialize VAD
print("Initializing VAD...")
vad = VoiceActivityDetector(threshold=0.5)
print("VAD Initialized.")

import traceback

# Piper Configuration
PIPER_DIR = os.path.join(os.getcwd(), "piper")
# Check for nested piper folder (common in windows zip)
if os.path.exists(os.path.join(PIPER_DIR, "piper", "piper.exe")):
    PIPER_EXE = os.path.join(PIPER_DIR, "piper", "piper.exe")
elif os.path.exists(os.path.join(PIPER_DIR, "piper.exe")):
    PIPER_EXE = os.path.join(PIPER_DIR, "piper.exe")
else:
    PIPER_EXE = "piper"
    print(f"Warning: piper.exe not found in {PIPER_DIR}. Using system 'piper'.")

print(f"Using Piper at: {PIPER_EXE}")
MODEL_PATH = os.path.join(PIPER_DIR, "en_US-ryan-medium.onnx")

# Audio Configuration
SAMPLE_RATE = 8000
CHANNELS = 1
CHUNK_SIZE = 160 # 20ms at 8000Hz
SILENCE_THRESHOLD = 500 # Adjust based on noise
SILENCE_DURATION = 1.5 # Seconds of silence to trigger processing

def get_weather(city="Hyderabad"):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude=17.3850&longitude=78.4867&current=temperature_2m,weather_code"
        response = requests.get(url)
        data = response.json()
        temp = data['current']['temperature_2m']
        return f"{temp} degrees Celsius"
    except Exception as e:
        print(f"Weather error: {e}")
        return "unknown weather"

@app.get("/")
async def get():
    return HTMLResponse("<h2>Morning Briefing AI Agent</h2><p>Server is running.</p>")

@app.post("/voice")
async def voice(request: Request):
    """Twilio webhook for incoming calls"""
    response_xml = f"""
    <Response>
        <Connect>
            <Stream url="wss://{request.headers.get('host')}/media-stream" />
        </Connect>
    </Response>
    """
    return HTMLResponse(content=response_xml, media_type="application/xml")

@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")
    
    stream_sid = None
    audio_buffer = bytearray()
    vad_buffer = bytearray()
    silence_start_time = None
    is_speaking = False
    
    current_task = None

    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            event = data.get("event")
            
            if event == "start":
                print(f"Media stream started: {data.get('start')}")
                stream_sid = data.get('streamSid')
                
                # Initial Greeting
                weather = get_weather()
                greeting = f"Good morning! It's currently {weather} in Hyderabad. How can I help you today?"
                # Run greeting in background so we can interrupt it too if needed (unlikely for greeting but good practice)
                current_task = asyncio.create_task(send_audio(websocket, greeting, stream_sid))
                
            elif event == "media":
                payload = data.get("media", {}).get("payload")
                if payload:
                    chunk = base64.b64decode(payload)
                    audio_buffer.extend(chunk)
                    
                    # VAD Check
                    # Buffer specifically for VAD to ensure enough context (Silero needs >30ms)
                    vad_buffer.extend(chunk)
                    
                    # Process VAD in chunks of exactly 256 bytes (32ms at 8000Hz)
                    # Silero VAD strictly requires 256 samples for 8000Hz
                    while len(vad_buffer) >= 256:
                        vad_chunk = vad_buffer[:256]
                        vad_buffer = vad_buffer[256:] # Remove processed chunk
                        
                        # Convert u-law to PCM
                        pcm_chunk = mulaw_to_pcm(bytes(vad_chunk))
                        
                        # Check for speech using Silero VAD
                        is_speech_detected = vad.is_speech(pcm_chunk)
                        
                        if is_speech_detected:
                            # INTERRUPTION LOGIC
                            if not is_speaking:
                                print("\nUser started speaking! Interrupting...", end="", flush=True)
                                
                                # 1. Cancel current processing/speaking task
                                if current_task and not current_task.done():
                                    current_task.cancel()
                                    print(" (Task cancelled)", end="")
                                
                                # 2. Clear Twilio Audio Buffer
                                clear_msg = {
                                    "event": "clear",
                                    "streamSid": stream_sid,
                                }
                                await websocket.send_text(json.dumps(clear_msg))
                                print(" (Audio cleared)")

                            is_speaking = True
                            silence_start_time = None
                            print(".", end="", flush=True) # Visual indicator of speech
                        else:
                            if is_speaking and silence_start_time is None:
                                silence_start_time = time.time()
                                print("!", end="", flush=True) # Visual indicator of silence start
                            
                    # Check for silence duration
                    if is_speaking and silence_start_time and (time.time() - silence_start_time > SILENCE_DURATION):
                        print("\nSilence detected, processing audio...")
                        is_speaking = False
                        silence_start_time = None
                        
                        # Process the buffer in background
                        # Cancel previous task if somehow still running (shouldn't be)
                        if current_task and not current_task.done():
                            current_task.cancel()
                            
                        current_task = asyncio.create_task(process_audio_input(websocket, audio_buffer.copy(), stream_sid))
                        audio_buffer = bytearray() # Clear buffer
                
            elif event == "stop":
                print("Media stream stopped")
                if current_task and not current_task.done():
                    current_task.cancel()
                
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        traceback.print_exc()
    finally:
        if current_task and not current_task.done():
            current_task.cancel()

async def process_audio_input(websocket: WebSocket, audio_data: bytearray, stream_sid: str):
    """Transcribe audio and generate response"""
    # 1. Save to WAV
    filename = f"temp_{int(time.time())}.wav"
    try:
        # Convert u-law buffer to PCM
        pcm_data = mulaw_to_pcm(bytes(audio_data))
        
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(8000)
            wf.writeframes(pcm_data)
            
        # 2. Transcribe (Groq Whisper)
        with open(filename, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(filename, file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
        
        user_text = transcription
        print(f"User said: {user_text}")
        
        if not user_text.strip():
            return # Ignore empty noise

        # 3. Generate Response (Groq Llama 3)
        # Query Knowledge Base
        kb = get_knowledge_base()
        context = kb.query(user_text) if kb else ""
        
        system_prompt = """You are an expert assistant for CognitBotz, an AI automation company. Your goal is to provide accurate, detailed answers based ONLY on the information provided in the context below.

IMPORTANT INSTRUCTIONS:
1. Read ALL the context carefully before answering.
2. If the context contains specific lists (like product names, services, etc.), include ALL items from those lists in your answer.
3. Provide complete and detailed information when available.
4. Format your answer clearly - use bullet points or numbering when listing multiple items.
5. If the question asks about "products" specifically, focus on named products like Docapture AI, Skill Matrix AI, and Intelligentic AI.
6. Never make up information not present in the context.
7. If the information is not in the context, say "I don't have that specific information available."
8. Be thorough and comprehensive in your response.
9. Do not start the answer with "Based on the context", act like a normal human answering questions about their company.
10. while answering do not include "confidence:" and "sources_used:", just the answer is enough.
"""
        if context:
            system_prompt += f"\n\nContext:\n{context}"
            print(f"RAG Context found: {context[:100]}...")

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_text,
                }
            ],
            model="llama-3.1-8b-instant",
            max_tokens=150,
        )
        
        response_text = chat_completion.choices[0].message.content
        print(f"AI response: {response_text}")
        
        # 4. Synthesize and Send (Piper)
        await send_audio(websocket, response_text, stream_sid)
        
    except Exception as e:
        print(f"Error processing input: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

async def send_audio(websocket: WebSocket, text: str, stream_sid: str):
    """Generate audio with Piper and stream to Twilio"""
    print(f"Generating audio for: {text}")
    
    try:
        # Run Piper in a separate thread to avoid blocking the event loop
        # and to bypass Windows asyncio subprocess issues
        def run_piper():
            return subprocess.run(
                [PIPER_EXE, "--model", MODEL_PATH, "--output-raw"],
                input=text.encode('utf-8'),
                capture_output=True
            )

        result = await asyncio.to_thread(run_piper)
        
        if result.returncode != 0:
            print(f"Piper error: {result.stderr.decode()}")
            return

        # Convert to u-law 8000Hz
        # Piper output is 22050Hz 16-bit mono PCM
        mulaw_audio = pcm_to_mulaw(result.stdout, sample_rate=22050, target_sample_rate=8000)
        
        # Chunk and send
        chunk_size = 1024 
        for i in range(0, len(mulaw_audio), chunk_size):
            chunk = mulaw_audio[i:i+chunk_size]
            payload = base64.b64encode(chunk).decode("utf-8")
            
            media_message = {
                "event": "media",
                "streamSid": stream_sid,
                "media": {
                    "payload": payload
                }
            }
            await websocket.send_text(json.dumps(media_message))
            
    except Exception as e:
        print(f"Error sending audio: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
