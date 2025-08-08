# luna/listen.py
"""
Handles Speech-to-Text (STT) functionality using OpenAI Whisper and PyAudio.
Refactored to use a persistent audio stream and run in an asyncio-compatible manner.
"""
try:
    import pyaudio
    import numpy as np
    import whisper
    AUDIO_DEPENDENCIES_AVAILABLE = True
except (ImportError, OSError) as e:
    AUDIO_DEPENDENCIES_AVAILABLE = False
    AUDIO_IMPORT_ERROR = str(e)

import tempfile
import asyncio
import time
from asyncio import Queue

from . import events
from .config import AUDIO_INPUT_DEVICE_INDEX

# Audio recording parameters
RATE = 16000
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
SILENCE_THRESHOLD = 3000 # Increased from 1500, making it less sensitive
SILENCE_LIMIT = 3 * (RATE // CHUNK) # 3 seconds of silence to trigger transcription

class AudioListener:
    def __init__(self):
        self._stop_event = asyncio.Event()
        self.audio_queue = Queue()
        self.whisper_model = None
        self.p = None
        self.stream = None
        self.listening = False
        
        if not AUDIO_DEPENDENCIES_AVAILABLE:
            events.publish("error", f"Audio dependencies not available: {AUDIO_IMPORT_ERROR}")
            events.publish("status_update", "Audio input disabled - text input only mode")

    async def load_whisper_model(self):
        if self.whisper_model is None:
            events.publish("status_update", "Loading Whisper model...")
            try:
                # Load model in a separate thread to avoid blocking the event loop
                self.whisper_model = await asyncio.to_thread(whisper.load_model, "base.en")
                events.publish("status_update", "Whisper model loaded.")
            except Exception as e:
                events.publish("error", f"Could not load Whisper model: {e}")
                self.whisper_model = None
        return self.whisper_model

    async def start_listening(self):
        if not AUDIO_DEPENDENCIES_AVAILABLE:
            events.publish("status_update", "Audio listening not available - skipping audio setup")
            return
            
        self.p = pyaudio.PyAudio()
        try:
            # Open stream in a separate thread to avoid blocking the event loop
            self.stream = await asyncio.to_thread(
                self.p.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=AUDIO_INPUT_DEVICE_INDEX
            )
            self.listening = True
            events.publish("status_update", "Listening for audio...")
        except Exception as e:
            events.publish("error", f"Failed to open audio stream: {e}. Check your microphone and ALSA/Jack configuration.")
            self.listening = False
            return

        frames = []
        silent_chunks = 0
        speaking = False

        while not self._stop_event.is_set():
            try:
                # Read audio data in a separate thread to avoid blocking the event loop
                data = await asyncio.to_thread(self.stream.read, CHUNK, exception_on_overflow=False)
                
                audio_data = np.frombuffer(data, dtype=np.int16)
                squared_mean = np.mean(np.square(audio_data))
                
                if audio_data.size == 0:
                    print("DEBUG: audio_data is empty.")
                if squared_mean < 0:
                    squared_mean = 1e-9 # Small positive number to avoid sqrt of negative
                rms = np.sqrt(squared_mean)

                print(f"RMS: {rms:.2f}")

                if rms < SILENCE_THRESHOLD:
                    silent_chunks += 1
                    if speaking and silent_chunks > SILENCE_LIMIT:
                        speaking = False
                        events.publish("status_update", "Transcribing...")
                        await self.transcribe_audio(frames) # Await transcription
                        frames = []
                        silent_chunks = 0
                        print("Silence detected, stopped recording.")
                else:
                    silent_chunks = 0
                    if not speaking:
                        speaking = True
                        events.publish("status_update", "Speech detected, recording...")
                        print("Speech detected, recording...")
                frames.append(data)
                
                # Yield control to the event loop
                await asyncio.sleep(0.001) 

            except Exception as e:
                events.publish("error", f"Audio listening error: {e}")
                break
        
        self.cleanup()

    async def transcribe_audio(self, frames):
        if not self.whisper_model and not await self.load_whisper_model(): # Await model loading
            events.publish("error", "Speech recognition unavailable.")
            return

        if not frames:
            return

        audio_np = np.frombuffer(b''.join(frames), dtype=np.int16).flatten().astype(np.float32) / 32768.0

        try:
            # Transcribe in a separate thread to avoid blocking the event loop
            result = await asyncio.to_thread(self.whisper_model.transcribe, audio_np, fp16=False)
            transcribed_text = result["text"].strip()
            print(f"Transcribed: '{transcribed_text}'")
            if transcribed_text:
                events.publish("user_input", transcribed_text)
        except Exception as e:
            events.publish("error", f"Whisper transcription failed: {e}")

    async def stop(self):
        self._stop_event.set()
        # Give a moment for the listening loop to recognize the stop event
        await asyncio.sleep(0.1) 
        self.cleanup()

    def cleanup(self):
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
        except Exception as e:
            events.publish("error", f"Error stopping audio stream: {e}")
        try:
            if self.p:
                self.p.terminate()
                self.p = None
        except Exception as e:
            events.publish("error", f"Error terminating PyAudio: {e}")
        self.listening = False
        events.publish("status_update", "Audio listener stopped.")