# luna/listen.py
"""
Handles Speech-to-Text (STT) functionality using OpenAI Whisper and PyAudio.
"""
import pyaudio
import numpy as np
import whisper
import tempfile
from . import events

# Audio recording parameters
RATE = 16000
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
SILENCE_THRESHOLD = 1500 # Increased from 1000, making it less sensitive
SILENCE_LIMIT = 3 * (RATE // CHUNK) # 3 seconds of silence to trigger transcription

model = None

def load_whisper_model():
    global model
    if model is None:
        events.publish("status_update", "Loading Whisper model...")
        try:
            model = whisper.load_model("base.en")
            events.publish("status_update", "Whisper model loaded.")
        except Exception as e:
            events.publish("error", f"Could not load Whisper model: {e}")
            model = None
    return model

def listen_and_transcribe(fallback_to_text: bool = False) -> str:
    """
    Listens to microphone input and transcribes it.
    Publishes events for status updates and the final transcription.
    """
    global model
    if model is None and load_whisper_model() is None:
        events.publish("error", "Speech recognition unavailable.")
        if fallback_to_text:
            return input("You: ")
        return ""

    p = None
    stream = None
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    except Exception as e:
        events.publish("error", f"Failed to open audio stream: {e}. Check your microphone and ALSA/Jack configuration.")
        if p:
            p.terminate()
        return ""

    frames = []
    silent_chunks = 0

    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(np.square(audio_data)))

            if rms < SILENCE_THRESHOLD:
                silent_chunks += 1
            else:
                silent_chunks = 0

            if silent_chunks > SILENCE_LIMIT and len(frames) > SILENCE_LIMIT:
                events.publish("status_update", "Transcribing...")
                break
        except KeyboardInterrupt:
            events.publish("system_shutdown")
            return "exit"
        except Exception as e:
            events.publish("error", f"Audio listening error: {e}")
            break
    
    stream.stop_stream()
    stream.close()
    p.terminate()

    if not frames:
        return ""

    audio_np = np.frombuffer(b''.join(frames), dtype=np.int16).flatten().astype(np.float32) / 32768.0

    try:
        result = model.transcribe(audio_np, fp16=False)
        transcribed_text = result["text"].strip()
        if transcribed_text:
            events.publish("user_input", transcribed_text)
        return transcribed_text
    except Exception as e:
        events.publish("error", f"Whisper transcription failed: {e}")
        return ""
