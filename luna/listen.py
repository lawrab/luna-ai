# luna/listen.py
"""
Handles Speech-to-Text (STT) functionality using OpenAI Whisper and PyAudio.
Refactored to use a persistent audio stream and run in a dedicated thread.
"""
import pyaudio
import numpy as np
import whisper
import tempfile
import threading
import time
from queue import Queue

from . import events
from .config import AUDIO_INPUT_DEVICE_INDEX

# Audio recording parameters
RATE = 16000
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
SILENCE_THRESHOLD = 3000 # Increased from 1500, making it less sensitive
SILENCE_LIMIT = 3 * (RATE // CHUNK) # 3 seconds of silence to trigger transcription

class AudioListener(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True  # Allow the main program to exit even if this thread is still running
        self._stop_event = threading.Event()
        self.audio_queue = Queue()
        self.whisper_model = None
        self.p = None
        self.stream = None
        self.listening = False

    def load_whisper_model(self):
        if self.whisper_model is None:
            events.publish("status_update", "Loading Whisper model...")
            try:
                self.whisper_model = whisper.load_model("base.en")
                events.publish("status_update", "Whisper model loaded.")
            except Exception as e:
                events.publish("error", f"Could not load Whisper model: {e}")
                self.whisper_model = None
        return self.whisper_model

    def run(self):
        self.p = pyaudio.PyAudio()
        try:
            self.stream = self.p.open(
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
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                # Debugging: Print raw data length and a sample
                # print(f"DEBUG: Raw data length: {len(data)}")
                # if len(data) > 0: print(f"DEBUG: Raw data sample (first 10 bytes): {data[:10]}")

                audio_data = np.frombuffer(data, dtype=np.int16)
                squared_mean = np.mean(np.square(audio_data))
                
                # Debugging: Print audio_data and squared_mean when issues occur
                if audio_data.size == 0:
                    print("DEBUG: audio_data is empty.")
                if squared_mean < 0:
                    print(f"DEBUG: squared_mean is negative: {squared_mean}. audio_data sample: {audio_data[:10]}")

                # Debugging: Check min/max of audio_data
                # if audio_data.size > 0:
                #     print(f"DEBUG: audio_data min: {audio_data.min()}, max: {audio_data.max()}")

                # Ensure squared_mean is non-negative before taking sqrt
                if squared_mean < 0:
                    squared_mean = 1e-9 # Small positive number to avoid sqrt of negative
                rms = np.sqrt(squared_mean)

                # Debugging: Print RMS value
                print(f"RMS: {rms:.2f}")

                if rms < SILENCE_THRESHOLD:
                    silent_chunks += 1
                    if speaking and silent_chunks > SILENCE_LIMIT:
                        speaking = False
                        events.publish("status_update", "Transcribing...")
                        self.transcribe_audio(frames)
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

            except Exception as e:
                events.publish("error", f"Audio listening error: {e}")
                break
        
        self.cleanup()

    def transcribe_audio(self, frames):
        if not self.whisper_model and not self.load_whisper_model():
            events.publish("error", "Speech recognition unavailable.")
            return

        if not frames:
            return

        audio_np = np.frombuffer(b''.join(frames), dtype=np.int16).flatten().astype(np.float32) / 32768.0

        try:
            result = self.whisper_model.transcribe(audio_np, fp16=False)
            transcribed_text = result["text"].strip()
            # Debugging: Print transcribed text
            print(f"Transcribed: '{transcribed_text}'")
            if transcribed_text:
                events.publish("user_input", transcribed_text)
        except Exception as e:
            events.publish("error", f"Whisper transcription failed: {e}")

    def stop(self):
        self._stop_event.set()

    def cleanup(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
        events.publish("status_update", "Audio listener stopped.")