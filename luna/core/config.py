"""
Configuration management with environment variable support and validation.
"""
import os
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .types import AppConfig, AudioConfig, LLMConfig, TTSConfig, LogLevel


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    """
    
    # Application settings
    app_name: str = "L.U.N.A."
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    data_dir: Path = Path.home() / ".luna"
    config_file: Optional[Path] = None
    
    # Audio settings
    audio_input_device_index: Optional[int] = None
    audio_sample_rate: int = 16000
    audio_chunk_size: int = 1024
    audio_channels: int = 1
    audio_silence_threshold: int = 3000
    audio_silence_limit_seconds: int = 3
    audio_whisper_model: str = "base.en"
    
    # LLM settings  
    llm_model_name: str = "llama3"
    llm_base_url: str = "http://localhost:11434"
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 3
    llm_temperature: float = 0.7
    
    # TTS settings
    tts_enabled: bool = True
    tts_engine: str = "espeak-ng"
    tts_voice: str = "en"
    tts_speed: int = 175
    tts_pitch: int = 50
    tts_volume: int = 100
    
    model_config = SettingsConfigDict(
        env_prefix="LUNA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    @field_validator('log_level', mode='before')
    @classmethod
    def validate_log_level(cls, v):
        if isinstance(v, str):
            return LogLevel(v.upper())
        return v
    
    @field_validator('data_dir', mode='before')
    @classmethod
    def validate_data_dir(cls, v):
        if isinstance(v, str):
            return Path(v).expanduser()
        return v
    
    @field_validator('audio_input_device_index', mode='before')
    @classmethod
    def validate_audio_device_index(cls, v):
        if isinstance(v, str) and v.strip() == '':
            return None
        return v
    
    def to_app_config(self) -> AppConfig:
        """Convert settings to AppConfig."""
        return AppConfig(
            debug=self.debug,
            log_level=self.log_level,
            audio=AudioConfig(
                input_device_index=self.audio_input_device_index,
                sample_rate=self.audio_sample_rate,
                chunk_size=self.audio_chunk_size,
                channels=self.audio_channels,
                silence_threshold=self.audio_silence_threshold,
                silence_limit_seconds=self.audio_silence_limit_seconds,
                whisper_model=self.audio_whisper_model,
            ),
            llm=LLMConfig(
                model_name=self.llm_model_name,
                base_url=self.llm_base_url,
                timeout_seconds=self.llm_timeout_seconds,
                max_retries=self.llm_max_retries,
                temperature=self.llm_temperature,
            ),
            tts=TTSConfig(
                enabled=self.tts_enabled,
                engine=self.tts_engine,
                voice=self.tts_voice,
                speed=self.tts_speed,
                pitch=self.tts_pitch,
                volume=self.tts_volume,
            ),
        )
    
    def ensure_data_dir(self) -> Path:
        """Ensure data directory exists and return it."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment and config files."""
    global _settings
    _settings = Settings()
    return _settings


class ConfigManager:
    """
    Configuration manager with support for multiple config sources.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or get_settings()
        self._app_config: Optional[AppConfig] = None
    
    @property
    def settings(self) -> Settings:
        return self._settings
    
    @property 
    def app_config(self) -> AppConfig:
        if self._app_config is None:
            self._app_config = self._settings.to_app_config()
        return self._app_config
    
    def reload(self) -> None:
        """Reload configuration from all sources."""
        self._settings = Settings()
        self._app_config = None
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self._settings.ensure_data_dir()
        
        # Create subdirectories
        (self._settings.data_dir / "logs").mkdir(exist_ok=True)
        (self._settings.data_dir / "models").mkdir(exist_ok=True)
        (self._settings.data_dir / "cache").mkdir(exist_ok=True)
    
    def get_log_file_path(self) -> Path:
        """Get the log file path."""
        return self._settings.data_dir / "logs" / "luna.log"
    
    def get_cache_dir(self) -> Path:
        """Get cache directory."""
        return self._settings.data_dir / "cache"
    
    def get_models_dir(self) -> Path:
        """Get models directory."""
        return self._settings.data_dir / "models"


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager