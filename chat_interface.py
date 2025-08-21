"""
Chat Frontend - интерактивный чат интерфейс.

Этот модуль предоставляет UI для общения с агентом в режиме чата.
Использует core_agent как бэкенд для обработки сообщений.
"""

from typing import Optional

from core_agent import AgentConfig, LLMProvider, process_user_message
from input_handler import cleanup_input_handler, enhanced_input, is_readline_available


def create_chat_session(provider: LLMProvider, model: Optional[str] = None) -> AgentConfig:
    """Create a new chat session with the specified provider."""
    config = AgentConfig(provider, model)
    config.initialize_client()
    return config


def print_welcome_message(config: AgentConfig):
    """Print welcome message for chat mode."""
    provider_name = config.get_provider_display_name()
    print(f"LLM Agent started in chat mode with {provider_name}")
    print("Type 'exit', 'quit', or press Ctrl+C to stop.")
    print("Type your message and press Enter to start chatting.")
    print("-" * 50)


def handle_chat_message(user_input: str, config: AgentConfig, verbose: bool = False) -> str:
    """Handle a single chat message and return the response."""
    try:
        result = process_user_message(
            user_input,
            config.provider,
            config.client,
            config.chat_history,
            return_usage=False,
            verbose=verbose,
            silent_mode=False,  # Chat mode is never silent
        )
        # Ensure we return just the string response
        return result if isinstance(result, str) else str(result)
    except Exception as e:
        return f"Error processing message: {str(e)}"


def run_chat_mode(provider: LLMProvider, model: Optional[str] = None, verbose: bool = False) -> None:
    """Run the interactive chat interface."""
    try:
        # Create chat session
        config = create_chat_session(provider, model)
        print_welcome_message(config)

        # Check if enhanced input is available
        if not is_readline_available():
            print("⚠️  Enhanced input features not available. Install 'readline' for better experience.")

        # Main chat loop
        while True:
            try:
                # Get user input with enhanced features if available
                user_input = enhanced_input("You: ").strip()

                # Check for exit commands
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("Goodbye!")
                    break

                if not user_input:
                    continue

                # Process message and get response
                print()  # Add spacing before response
                response = handle_chat_message(user_input, config, verbose)

                # Print response
                print(f"Agent: {response}")
                print()  # Add spacing after response

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except EOFError:
                print("\nGoodbye!")
                break

    except Exception as e:
        print(f"Error starting chat session: {e}")

    finally:
        # Cleanup input handler
        cleanup_input_handler()


def chat_main(provider: LLMProvider, model: Optional[str] = None, verbose: bool = False) -> None:
    """Main entry point for chat mode."""
    run_chat_mode(provider, model, verbose)
