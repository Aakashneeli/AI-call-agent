# AI Voice Agent (CognitBotz)

A real-time, low-latency AI voice agent capable of handling phone calls, answering technical questions using RAG (Retrieval-Augmented Generation), and handling interruptions naturally with VAD (Voice Activity Detection).

## Features

*   **Real-time Interaction:** Uses Twilio Media Streams for bi-directional audio.
*   **Ultra-Fast Inference:** Powered by Groq (Llama 3) and Groq Whisper.
*   **Local TTS:** Uses Piper TTS for near-zero latency speech synthesis.
*   **Advanced RAG:** Ingests PDF documents, uses hybrid search (keyword + semantic), and persists the vector index.
*   **Barge-In Support:** Users can interrupt the AI, and it will stop speaking immediately (Silero VAD).

## Prerequisites

*   Python 3.10+
*   [Ngrok](https://ngrok.com/) (for local development tunneling)
*   Twilio Account (with a phone number)
*   Groq API Key

## Detailed Setup Guide

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

### 2. Python Environment Setup
It's best to use a virtual environment to keep dependencies isolated.
```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\activate

# Activate it (Mac/Linux)
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*Note: If you encounter errors with PyTorch, install it manually from [pytorch.org](https://pytorch.org/get-started/locally/).*

### 4. Download Piper TTS (Critical Step)
The voice generation runs locally using Piper. You must download the binary and model manually.

1.  **Download Piper Executable:**
    *   Visit [Piper Releases](https://github.com/rhasspy/piper/releases).
    *   Download the zip file matching your OS (e.g., `piper_windows_amd64.zip`).
    *   Extract it. You will find a folder containing `piper.exe` (or just `piper`).
    *   **Action:** Create a folder named `piper` inside the project root. Move the `piper.exe` (and other extracted files like `espeak-ng-data`) into this `piper` folder.

2.  **Download Voice Model:**
    *   We use the `en_US-ryan-medium` voice.
    *   Download [en_US-ryan-medium.onnx](https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx?download=true)
    *   Download [en_US-ryan-medium.onnx.json](https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx.json?download=true)
    *   **Action:** Move both files into the `piper` folder you created above.

**Check your folder structure:**
```
AI-call-agent/
├── piper/
│   ├── piper.exe
│   ├── en_US-ryan-medium.onnx
│   └── en_US-ryan-medium.onnx.json
├── server.py
├── ...
```

### 5. Ngrok Setup (Critical for Twilio)
Ngrok exposes your local server to the internet so Twilio can talk to it.

1.  **Create Account:**
    *   Go to [ngrok.com](https://ngrok.com/) and sign up for a free account.

2.  **Download:**
    *   Go to your [Ngrok Dashboard](https://dashboard.ngrok.com/get-started/setup).
    *   Download the version for your OS.
    *   Unzip it. You will see `ngrok.exe`.

3.  **Authenticate:**
    *   Copy your Authtoken from the dashboard.
    *   Open your terminal where `ngrok.exe` is.
    *   Run:
        ```bash
        ngrok config add-authtoken <YOUR_AUTH_TOKEN>
        ```

### 6. Environment Variables
Create a file named `.env` in the root directory. Add the following keys:

```env
# Get this from https://console.groq.com/keys
GROQ_API_KEY=gsk_...

# Get these from https://console.twilio.com/
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...

# Your Twilio Phone Number (must be purchased in Twilio console)
TWILIO_PHONE_NUMBER=+1234567890

# Your Personal Phone Number (for testing outbound calls if needed)
MY_PHONE_NUMBER=+1987654321
```

### 7. RAG Data Setup
*   Create a folder named `data` in the root directory.
*   Place your PDF documents (e.g., `Company_Profile.pdf`, `RFP_Requirements.pdf`) inside this folder.
*   The system will automatically ingest them when you start the server.

## Running the Application

### Step 1: Start Ngrok Tunnel
Twilio needs a public URL to talk to your local server.
```bash
ngrok http 8000
```
*   Copy the "Forwarding" URL (looks like `https://xyz.ngrok-free.app`).
*   Keep this terminal window open!

### Step 2: Configure Twilio Webhook
1.  Log in to Twilio Console.
2.  Go to **Phone Numbers** > **Manage** > **Active Numbers**.
3.  Click on your phone number.
4.  Scroll down to **Voice & Fax**.
5.  Under **"A Call Comes In"**, select **Webhook**.
6.  Paste your Ngrok URL followed by `/voice`.
    *   Example: `https://xyz.ngrok-free.app/voice`
7.  Ensure HTTP Method is **POST**.
8.  Click **Save**.

### Step 3: Start the Server
Open a new terminal (keep Ngrok running in the other one), activate your venv, and run:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```
*   You should see "Application startup complete".
*   If it says "Building vector index...", wait for it to finish processing your PDFs.

### Step 4: Test It
Call your Twilio phone number. The agent should pick up and greet you!

## Troubleshooting

*   **"Input audio chunk is too short":** This means VAD is receiving incorrect chunk sizes. Ensure you haven't modified the 256-byte chunking logic in `server.py`.
*   **Piper error / No audio:** Check that `piper.exe` is in the correct folder and the path in `server.py` matches your system.
*   **RAG not answering correctly:**
    *   Check if `data/` folder has PDFs.
    *   Delete the `faiss_index` folder and restart the server to force a rebuild.
    *   Check the server logs to see if it retrieved the correct document.
