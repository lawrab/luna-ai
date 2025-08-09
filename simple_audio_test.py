#!/usr/bin/env python3
"""
Simple audio test without numpy to debug microphone input.
"""
import pyaudio
import time
import struct
import math

def test_microphone():
    """Test microphone input without external dependencies."""
    print("🎤 Simple Microphone Test")
    print("=" * 50)
    
    # Audio parameters
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    THRESHOLD = 3000
    
    p = pyaudio.PyAudio()
    
    try:
        # List devices first
        print("Available audio devices:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  {i}: {info['name']} (channels: {info['maxInputChannels']})")
        print()
        
        # Try to open stream with default device
        print("Opening audio stream...")
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        print("✓ Audio stream opened successfully")
        print()
        
        print("🎯 Voice Detection Test")
        print(f"Threshold: {THRESHOLD}")
        print("Speak into your microphone. Press Ctrl+C to stop.")
        print()
        
        chunk_count = 0
        max_rms = 0
        min_rms = float('inf')
        
        try:
            while True:
                # Read audio data
                data = stream.read(CHUNK, exception_on_overflow=False)
                chunk_count += 1
                
                # Convert to integers
                audio_ints = struct.unpack(f'{CHUNK}h', data)
                
                # Calculate RMS manually
                sum_squares = sum(x * x for x in audio_ints)
                mean_square = sum_squares / len(audio_ints)
                rms = math.sqrt(mean_square)
                
                # Track statistics
                max_rms = max(max_rms, rms)
                min_rms = min(min_rms, rms)
                
                # Voice activity detection
                is_speech = rms >= THRESHOLD
                status = "🔊 SPEECH" if is_speech else "🔇 silence"
                
                # Print every few chunks
                if chunk_count % 5 == 0:
                    print(f"Chunk {chunk_count:4d}: RMS={rms:8.1f} | {status} | Range: {min_rms:.1f}-{max_rms:.1f}")
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print(f"\n📊 Statistics:")
            print(f"  Chunks processed: {chunk_count}")
            print(f"  RMS Range: {min_rms:.1f} - {max_rms:.1f}")
            print(f"  Current Threshold: {THRESHOLD}")
            
            if max_rms > 0:
                suggested_threshold = min_rms + (max_rms - min_rms) * 0.3
                print(f"  Suggested Threshold: {suggested_threshold:.0f}")
            
        finally:
            stream.stop_stream()
            stream.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        p.terminate()

if __name__ == "__main__":
    test_microphone()