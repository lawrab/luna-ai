# luna/config.py
"""
Legacy configuration file - kept for backward compatibility.
New configuration is in luna/core/config.py
"""
import warnings
from .core.config import get_settings

# Backward compatibility - these will be deprecated
warnings.warn(
    "Using luna.config is deprecated. Use luna.core.config instead.",
    DeprecationWarning,
    stacklevel=2
)

_settings = get_settings()

# Legacy exports
LLM_MODEL = _settings.llm_model_name
AUDIO_INPUT_DEVICE_INDEX = _settings.audio_input_device_index