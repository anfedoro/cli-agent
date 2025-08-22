"""
CLI Agent Configuration Management

Handles creation and management of configuration directory for storing
agent settings, chat history, and other persistent data.
Cross-platform unified approach using ~/.cliagent on all platforms.
"""

import json
from pathlib import Path


def get_config_dir() -> Path:
    """Get the configuration directory path based on OS.

    - Unix/macOS: ~/.cliagent
    - Windows: ~/.cliagent (unified approach for simplicity)

    Returns:
        Path to configuration directory
    """
    home = Path.home()

    # Use unified approach: ~/.cliagent on all platforms
    # This simplifies cross-platform development and user experience
    return home / ".cliagent"


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
        Path to history.txt in configuration directory
        (All platforms: ~/.cliagent/history.txt)
    """
    return ensure_config_dir() / "history.txt"


def get_settings_file() -> Path:
    """Get the settings file path.

    Returns:
        Path to settings.json in configuration directory
        (All platforms: ~/.cliagent/settings.json)
    """
    return ensure_config_dir() / "settings.json"


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
            "default_model": None,  # Model to use by default (provider-specific)
            "default_mode": "chat",  # Default mode: "chat" or "shell"
            "history_length": 1000,
            "completion_enabled": True,
            "preserve_initial_location": True,  # Return to starting directory on exit
            "agent_prompt_indicator": "⭐",  # Symbol to show in prompt when in agent mode
            "created_at": str(config_dir.stat().st_ctime) if config_dir.exists() else None,
        }

        with open(settings_file, "w") as f:
            json.dump(default_settings, f, indent=2)


def cleanup_config() -> None:
    """Cleanup function for configuration."""
    # Currently no cleanup needed, but could be used for
    # cleaning temporary files, closing connections, etc.
    pass


def load_settings() -> dict:
    """Load settings from config file.

    Returns:
        Dictionary with settings, or default settings if file doesn't exist
    """
    settings_file = get_settings_file()
    if settings_file.exists():
        try:
            import json

            with open(settings_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # Return default settings if file doesn't exist or is corrupted
    return {
        "version": "0.3.0",
        "default_provider": "openai",
        "default_model": None,
        "default_mode": "chat",
        "history_length": 1000,
        "completion_enabled": True,
        "preserve_initial_location": True,
        "agent_prompt_indicator": "⭐",
        "created_at": None,
    }


def save_settings(settings: dict) -> None:
    """Save settings to config file.

    Args:
        settings: Dictionary with settings to save
    """
    settings_file = get_settings_file()
    try:
        import json

        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Error saving settings: {e}")


def update_configuration(updates: dict) -> dict:
    """Update configuration settings.

    Args:
        updates: Dictionary with configuration updates.
                Supported keys: default_provider, default_model, default_mode,
                agent_prompt_indicator, preserve_initial_location, completion_enabled

    Returns:
        Dictionary with result status and updated settings
    """
    try:
        # Load current settings
        current_settings = load_settings()

        # Validate and apply updates
        valid_keys = {"default_provider", "default_model", "default_mode", "agent_prompt_indicator", "preserve_initial_location", "completion_enabled", "history_length"}

        valid_providers = {"openai", "gemini", "lmstudio"}
        valid_modes = {"chat", "shell"}

        updated_settings = current_settings.copy()
        applied_updates = {}

        for key, value in updates.items():
            if key not in valid_keys:
                continue

            # Validate specific settings
            if key == "default_provider" and value not in valid_providers:
                continue
            elif key == "default_mode" and value not in valid_modes:
                continue
            elif key in ["preserve_initial_location", "completion_enabled"] and not isinstance(value, bool):
                continue
            elif key == "history_length" and (not isinstance(value, int) or value < 1):
                continue

            updated_settings[key] = value
            applied_updates[key] = value

        # Save updated settings
        save_settings(updated_settings)

        return {
            "success": True,
            "message": f"Configuration updated successfully. Applied changes: {applied_updates}",
            "updated_settings": applied_updates,
            "current_settings": updated_settings,
        }

    except Exception as e:
        return {"success": False, "message": f"Error updating configuration: {e}", "updated_settings": {}, "current_settings": load_settings()}


def get_setting(key: str, default=None):
    """Get a specific setting value.

    Args:
        key: Setting key to retrieve
        default: Default value if key not found

    Returns:
        Setting value or default
    """
    settings = load_settings()
    return settings.get(key, default)
