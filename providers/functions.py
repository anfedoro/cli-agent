"""Function mappings for LLM providers.

This module contains dictionaries that map provider names to their corresponding functions.
Each dictionary represents a specific function that all providers must implement.
"""

from . import gemini, openai

# Initialize client functions
INITIALIZE_CLIENT = {
    "openai": openai.initialize_client,
    "gemini": gemini.initialize_client,
}

# Get available tools functions
GET_AVAILABLE_TOOLS = {
    "openai": openai.get_available_tools,
    "gemini": gemini.get_available_tools,
}

# Get display name functions
GET_DISPLAY_NAME = {
    "openai": openai.get_display_name,
    "gemini": gemini.get_display_name,
}

# Send message functions
SEND_MESSAGE = {
    "openai": openai.send_message,
    "gemini": gemini.send_message,
}

# Extract function calls functions
EXTRACT_FUNCTION_CALLS = {
    "openai": openai.extract_function_calls,
    "gemini": gemini.extract_function_calls,
}

# Add function result to messages functions
ADD_FUNCTION_RESULT_TO_MESSAGES = {
    "openai": openai.add_function_result_to_messages,
    "gemini": gemini.add_function_result_to_messages,
}

# Extract usage info functions
EXTRACT_USAGE_INFO = {
    "openai": openai.extract_usage_info,
    "gemini": gemini.extract_usage_info,
}

# Get response text functions
GET_RESPONSE_TEXT = {
    "openai": openai.get_response_text,
    "gemini": gemini.get_response_text,
}
