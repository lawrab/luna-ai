# luna/listen.py
"""
Handles Speech-to-Text (STT) functionality using OpenAI Whisper and PyAudio.
"""
import pyaudio
import numpy as np
import whisper
import tempfile
import os
import sys

# Audio recording parameters
RATE = 16000
CHUNK = 1024 # Smaller chunk size for more frequent processing
FORMAT = pyaudio.paInt16
CHANNELS = 1

# Global Whisper model variable
model = None

def load_whisper_model():
    global model
    if model is None:
        print("L.U.N.A: Loading Whisper model (this may take a moment)...", file=sys.stderr)
        try:
            # Use a small model for faster loading and inference
            model = whisper.load_model("base.en") # or "tiny.en", "small.en"
            print("L.U.N.A: Whisper model loaded.", file=sys.stderr)
        except Exception as e:
            print(f"L.U.N.A: Error loading Whisper model: {e}", file=sys.stderr)
            print("L.U.N.A: Please ensure you have an internet connection for the first run to download the model,", file=sys.stderr)
            print("L.U.N.A: or download it manually and place it in ~/.cache/whisper.", file=sys.stderr)
            model = None
    return model

def listen_and_transcribe() -> str:
    """
    Listens to microphone input, transcribes it using Whisper after a pause in speech.
    Returns the final transcribed text.
    """
    global model
    if model is None:
        model = load_whisper_model()
        if model is None:
            print("L.U.N.A: Speech recognition is unavailable. Falling back to text input.", file=sys.stderr)
            return input("You: ") # Fallback to text input if model fails to load

    p = pyaudio.PyAudio()

    print("\nL.U.N.A: Listening... (Speak and then pause to transcribe)")
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    frames = []
    silent_chunks = 0
    # Adjust these thresholds based on your environment and microphone sensitivity
    SILENCE_THRESHOLD = 500 # RMS energy below this is considered silence
    SILENCE_LIMIT = 2 * (RATE // CHUNK) # 2 seconds of silence to trigger transcription

    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

            # Convert audio chunk to numpy array for RMS calculation
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(np.square(audio_data)))

            if rms < SILENCE_THRESHOLD:
                silent_chunks += 1
            else:
                silent_chunks = 0 # Reset if speech is detected

            if silent_chunks > SILENCE_LIMIT and len(frames) > SILENCE_LIMIT: # Ensure some audio has been captured
                print("\rL.U.N.A: Transcribing...", end='', flush=True)
                break # Stop recording after silence

    except KeyboardInterrupt:
        print("\nL.U.N.A: Stopping listening.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    if not frames:
        print("\rYou: ", end='', flush=True)
        return "" # No audio captured

    # Concatenate all frames and convert to a numpy array suitable for Whisper
    audio_np = np.frombuffer(b''.join(frames), dtype=np.int16).flatten().astype(np.float32) / 32768.0

    # Save to a temporary WAV file for Whisper processing
    # Whisper can also take numpy arrays directly, but sometimes file is more robust
    # Let's use the numpy array directly for efficiency
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio_file:
        # Whisper expects 16kHz mono audio, which we are already recording
        # No need for complex audio file writing, just save the raw data
        # However, whisper.load_audio expects a file path or a numpy array
        pass # We don't need the file, just the numpy array

    try:
        # Transcribe the audio
        result = model.transcribe(audio_np, fp16=False) # fp16=False for CPU inference
        transcribed_text = result["text"].strip()
    except Exception as e:
        print(f"\nL.U.N.A: Error during Whisper transcription: {e}", file=sys.stderr)
        transcribed_text = ""

    print(f"\rYou: {transcribed_text}", flush=True)
    return transcribed_text

if __name__ == '__main__':
    print("Starting direct listen test...")
    transcribed_text = listen_and_transcribe()
    print(f"\nFinal Transcribed Text: {transcribed_text}")