# luna/config.py
"""
Centralized configuration settings for the L.U.N.A. assistant.
"""

# Name of the Ollama model to use for the assistant
LLM_MODEL = "llama3"

# Audio input device index for PyAudio. Set to None to use the default device.
# To find available device indices, run the `list_audio_devices.py` script
# located in the `scripts` directory.
AUDIO_INPUT_DEVICE_INDEX = 3