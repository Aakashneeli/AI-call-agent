# Project: AI Voice Agent for CognitBotz

## Problem Statement
The goal was to build a **low-latency, real-time AI Voice Agent** capable of:
1.  Handling phone calls via Twilio.
2.  Answering complex, technical questions based on specific company documents (RFPs, brochures).
3.  Maintaining a natural conversational flow, including the ability to handle interruptions ("barge-in").

## Solution Overview
We implemented a high-performance Python backend using **FastAPI** and **WebSockets** to orchestrate the audio stream.

### Core Architecture
*   **Telephony:** Twilio Media Streams (Bi-directional Audio).
*   **LLM (Brain):** Groq API (Llama 3) for ultra-fast inference.
*   **STT (Ears):** Groq Whisper for transcription.
*   **TTS (Mouth):** Piper (Local ONNX model) for near-zero latency speech synthesis.

### Key Features Implemented

#### 1. Advanced RAG (Retrieval-Augmented Generation)
*   **Multi-Doc Ingestion:** Automatically loads all PDFs from the `data/` directory.
*   **Smart Scoring:** Uses a custom scoring algorithm to prioritize documents containing key technical terms (e.g., "requirements", "scope") and specific filenames.
*   **Persistence:** The vector index (`faiss_index`) is saved to disk, so the "brain" doesn't need to be rebuilt on every restart.
*   **Strict Prompting:** The system prompt is engineered to prevent hallucinations and force the agent to cite its sources.

#### 2. Robust VAD (Voice Activity Detection)
*   **Silero VAD:** Integrated the industry-standard Silero model for precise speech detection.
*   **Barge-In Logic:** The agent listens *while* speaking. If it detects user speech, it instantly cancels the current audio stream and clears the buffer, allowing for natural interruptions.

### Current Status
- [x] Server & Twilio Integration
- [x] RAG Knowledge Base (Optimized)
- [x] VAD & Interruption Handling
- [ ] Frontend Dashboard (Next Step)
