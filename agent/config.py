"""
Configuration and data directory management for CLI Agent.

Handles creation and management of ~/.cliagent directory for storing
history, settings, and other persistent data.
"""

from pathlib import Path


def get_config_dir() -> Path:
    """Get the CLI Agent configuration directory path.
    
    Returns:
        Path to ~/.cliagent directory
    """
    home = Path.home()
    return home / '.cliagent'


def ensure_config_dir() -> Path:
    """Ensure the configuration directory exists.
    
    Creates ~/.cliagent directory if it doesn't exist.
    
    Returns:
        Path to the configuration directory
    """
    config_dir = get_config_dir()
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_history_file() -> Path:
    """Get the history file path.
    
    Returns:
        Path to ~/.cliagent/history.txt
    """
    return ensure_config_dir() / 'history.txt'


def get_settings_file() -> Path:
    """Get the settings file path.
    
    Returns:
        Path to ~/.cliagent/settings.json
    """
    return ensure_config_dir() / 'settings.json'


def initialize_config() -> None:
    """Initialize configuration directory and files if they don't exist."""
    config_dir = ensure_config_dir()
    
    # Create history file if it doesn't exist
    history_file = get_history_file()
    if not history_file.exists():
        history_file.touch()
    
    # Create basic settings file if it doesn't exist
    settings_file = get_settings_file()
    if not settings_file.exists():
        import json
        default_settings = {
            "version": "0.3.0",
            "default_provider": "openai",
            "history_length": 1000,
            "completion_enabled": True,
            "created_at": str(config_dir.stat().st_ctime) if config_dir.exists() else None
        }
        
        with open(settings_file, 'w') as f:
            json.dump(default_settings, f, indent=2)


def cleanup_config() -> None:
    """Cleanup function for configuration."""
    # Currently no cleanup needed, but could be used for
    # cleaning temporary files, closing connections, etc.
    pass
