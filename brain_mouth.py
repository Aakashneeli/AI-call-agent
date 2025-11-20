import os
import subprocess
import sys
import time
from dotenv import load_dotenv
from groq import Groq
import pyaudio
import wave

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("Error: GROQ_API_KEY not found in .env")
    sys.exit(1)

client = Groq(api_key=GROQ_API_KEY)

# Configuration
# Assuming piper is extracted in 'piper' folder in current directory
# Check if piper.exe is in piper/ or piper/piper/
PIPER_DIR = os.path.join(os.getcwd(), "piper")
if os.path.exists(os.path.join(PIPER_DIR, "piper.exe")):
    PIPER_EXE = os.path.join(PIPER_DIR, "piper.exe")
elif os.path.exists(os.path.join(PIPER_DIR, "piper", "piper.exe")):
    PIPER_EXE = os.path.join(PIPER_DIR, "piper", "piper.exe")
else:
    print("Warning: piper.exe not found. Please ensure it is downloaded and extracted in 'piper' directory.")
    PIPER_EXE = "piper" # Fallback to system path

MODEL_PATH = os.path.join(PIPER_DIR, "en_US-lessac-medium.onnx")

def generate_response(prompt):
    """Generate text response from Groq (Llama 3)"""
    start_time = time.time()
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful, casual assistant. Keep your responses concise and conversational.",
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.1-8b-instant",
        max_tokens=100,
    )
    response_text = chat_completion.choices[0].message.content
    latency = (time.time() - start_time) * 1000
    print(f"\n[Brain] Response ({latency:.0f}ms): {response_text}")
    return response_text

def speak(text):
    """Synthesize speech using Piper and play it"""
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model file not found at {MODEL_PATH}")
        return

    start_time = time.time()
    
    # Piper command: echo text | piper --model model.onnx --output_raw
    # We use --output_raw to get raw PCM data (16-bit, mono, 22050Hz usually for this model)
    
    try:
        process = subprocess.Popen(
            [PIPER_EXE, "--model", MODEL_PATH, "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE # Hide stderr logs
        )
        
        # Send text to stdin
        # Ensure text is encoded
        stdout_data, stderr_data = process.communicate(input=text.encode('utf-8'))
        
        if process.returncode != 0:
            print(f"Piper error: {stderr_data.decode('utf-8')}")
            return

        tts_latency = (time.time() - start_time) * 1000
        print(f"[Mouth] TTS Latency: {tts_latency:.0f}ms")

        # Play audio
        # Piper raw output is usually 22050Hz, 16-bit, mono
        play_audio(stdout_data)

    except Exception as e:
        print(f"Error running Piper: {e}")

def play_audio(audio_data):
    """Play raw PCM audio using PyAudio"""
    p = pyaudio.PyAudio()
    
    # Configuration for en_US-lessac-medium.onnx (usually 22050Hz)
    # If it sounds fast/slow, adjust rate.
    RATE = 22050
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True)
    
    stream.write(audio_data)
    stream.stop_stream()
    stream.close()
    p.terminate()

def main():
    print("--- Brain & Mouth Prototype ---")
    print("Type 'quit' to exit.")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break
        
        response = generate_response(user_input)
        speak(response)

if __name__ == "__main__":
    main()
