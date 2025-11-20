import torch
import numpy as np

class VoiceActivityDetector:
    def __init__(self, threshold=0.5):
        self.model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                           model='silero_vad',
                                           force_reload=False,
                                           onnx=False)
        (self.get_speech_timestamps,
         self.save_audio,
         self.read_audio,
         self.VADIterator,
         self.collect_chunks) = utils
        
        self.threshold = threshold
        self.sample_rate = 8000  # Twilio uses 8000Hz
        self.model.eval()
        print("Silero VAD initialized")

    def is_speech(self, audio_chunk_pcm: bytes) -> bool:
        """
        Check if the given PCM audio chunk contains speech.
        Expects 16-bit PCM audio at 8000Hz.
        """
        # Convert bytes to numpy array (float32)
        # Twilio sends mulaw, but we convert to PCM before calling this
        # Incoming PCM is 16-bit int
        audio_int16 = np.frombuffer(audio_chunk_pcm, dtype=np.int16)
        
        # Normalize to float32 between -1 and 1
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        # Convert to torch tensor
        audio_tensor = torch.from_numpy(audio_float32)
        
        # Add batch dimension if needed, but Silero expects 1D tensor for single chunk usually
        # actually, for streaming, it might be different. 
        # Let's use the simple model(x, sr) call which returns probability.
        
        with torch.no_grad():
            speech_prob = self.model(audio_tensor, self.sample_rate).item()
            
        return speech_prob > self.threshold
