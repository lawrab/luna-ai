#!/usr/bin/env python3
"""
Audio debugging script to test microphone input and voice detection.
"""
import asyncio
import time
import numpy as np
from luna.services.audio import AudioDevice
from luna.core.config import get_config_manager

def test_audio_levels():
    """Test audio input levels and voice activity detection."""
    print("🎤 Audio Input Debugging Tool")
    print("=" * 50)
    
    config = get_config_manager()
    audio_config = config.app_config.audio
    
    print(f"Audio Config:")
    print(f"  Device Index: {audio_config.input_device_index}")
    print(f"  Sample Rate: {audio_config.sample_rate}Hz")
    print(f"  Chunk Size: {audio_config.chunk_size}")
    print(f"  Channels: {audio_config.channels}")
    print(f"  Silence Threshold: {audio_config.silence_threshold}")
    print()
    
    try:
        with AudioDevice(audio_config) as device:
            print(f"✓ Audio device opened successfully")
            print(f"  Selected Device: {device._selected_device_index}")
            print(f"  Selected Sample Rate: {device._selected_sample_rate}Hz")
            print()
            
            print("🎯 Voice Activity Detection Test")
            print("Speak into your microphone. Press Ctrl+C to stop.")
            print(f"Silence threshold: {audio_config.silence_threshold}")
            print("RMS values will be shown in real-time:")
            print()
            
            chunk_count = 0
            max_rms = 0
            min_rms = float('inf')
            
            try:
                while True:
                    # Read audio chunk
                    chunk = device.read(audio_config.chunk_size)
                    chunk_count += 1
                    
                    # Calculate RMS
                    audio_data = np.frombuffer(chunk, dtype=np.int16)
                    rms = np.sqrt(np.mean(np.square(audio_data.astype(np.float32))))
                    
                    # Track min/max
                    max_rms = max(max_rms, rms)
                    min_rms = min(min_rms, rms)
                    
                    # Voice activity detection
                    is_speech = rms >= audio_config.silence_threshold
                    status = "🔊 SPEECH" if is_speech else "🔇 silence"
                    
                    # Print every 10th chunk to avoid spam
                    if chunk_count % 5 == 0:
                        print(f"Chunk {chunk_count:4d}: RMS={rms:8.1f} | {status} | Min={min_rms:.1f} Max={max_rms:.1f}")
                    
                    time.sleep(0.01)  # Small delay
                    
            except KeyboardInterrupt:
                print(f"\n📊 Statistics:")
                print(f"  Chunks processed: {chunk_count}")
                print(f"  RMS Range: {min_rms:.1f} - {max_rms:.1f}")
                print(f"  Silence Threshold: {audio_config.silence_threshold}")
                print(f"  Recommended threshold: {min_rms * 2:.0f} - {max_rms * 0.3:.0f}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_audio_levels()