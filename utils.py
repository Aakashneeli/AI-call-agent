import audioop
import numpy as np

def pcm_to_mulaw(pcm_data: bytes, sample_rate: int = 22050, target_sample_rate: int = 8000) -> bytes:
    """
    Convert PCM audio data to u-law format.
    Assumes input is 16-bit PCM.
    """
    # Resample if necessary (simple decimation for now, better to use scipy.signal.resample for quality)
    # For this prototype, we'll assume the input is already close or we'll just take every Nth sample
    # But ideally we should use a proper library. 
    # Let's use audioop for ratecv if possible, or just simple slicing for speed if quality isn't paramount yet.
    
    # Actually, audioop.ratecv is good.
    # state = None
    # new_fragment, state = audioop.ratecv(pcm_data, 2, 1, sample_rate, target_sample_rate, state)
    
    # But audioop is deprecated in 3.11 and removed in 3.13. 
    # Since we are targeting 3.10+, we can use it, but let's try to be future proof if possible.
    # However, for "Maximize open-source usage and minimize latency", audioop is fast (C implementation).
    
    # Let's stick to audioop for now as it's standard in 3.10.
    
    try:
        # Convert to mono if needed (assuming input might be stereo, but Piper usually outputs mono)
        # pcm_data is bytes.
        
        # Resample
        # width=2 (16-bit), nchannels=1
        converted_fragment, _ = audioop.ratecv(pcm_data, 2, 1, sample_rate, target_sample_rate, None)
        
        # Encode to u-law
        mulaw_data = audioop.lin2ulaw(converted_fragment, 2)
        
        return mulaw_data
    except Exception as e:
        print(f"Error in pcm_to_mulaw: {e}")
        return b""

def mulaw_to_pcm(mulaw_data: bytes) -> bytes:
    """
    Convert u-law audio data to PCM format.
    """
    try:
        # Decode from u-law to 16-bit PCM
        pcm_data = audioop.ulaw2lin(mulaw_data, 2)
        return pcm_data
    except Exception as e:
        print(f"Error in mulaw_to_pcm: {e}")
        return b""
