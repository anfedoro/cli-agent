import argparse

from interface.chat_interface import chat_main
from interface.shell_interface import shell_main
from agent.config import initialize_config, get_setting


def main():
    """Main entry point for the CLI agent."""
    # Initialize configuration directory on first run
    initialize_config()

    # Get default values from configuration
    default_provider = get_setting("default_provider", "openai")
    default_model = get_setting("default_model", None)
    default_mode = get_setting("default_mode", "chat")

    parser = argparse.ArgumentParser(description="CLI Agent")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed token usage information")
    parser.add_argument("--provider", "-p", choices=["openai", "gemini", "lmstudio"], default=default_provider, help=f"LLM provider to use (default: {default_provider})")
    parser.add_argument("--model", "-m", default=default_model, help="Model to use for the selected provider")
    parser.add_argument("--no-reasoning", action="store_true", help="Disable reasoning process for faster responses (LM Studio)")
    parser.add_argument("--mode", choices=["chat", "shell"], default=default_mode, help=f"Run mode: chat (conversation) or shell (command mode) (default: {default_mode})")
    parser.add_argument("--trace", "-t", action="store_true", help="Enable trace mode (show LLM execution details, only in shell mode)")
    parser.add_argument("--system-prompt-file", help="Path to a Markdown/text file with custom system prompt (session-scoped override)")
    parser.add_argument("--no-restore", action="store_true", help="Don't restore initial directory on exit (shell mode only)")
    args = parser.parse_args()

    # Apply session-scoped system prompt override via environment
    if args.system_prompt_file:
        import os
        os.environ["CLI_AGENT_SYSTEM_PROMPT_FILE"] = args.system_prompt_file

    if args.mode == "shell":
        # Shell mode: standard shell prompt with intelligent routing
        # Override preserve_initial_location setting if --no-restore is specified
        preserve_location = not args.no_restore
        shell_main(provider=args.provider, model=args.model, trace=args.trace or args.verbose, preserve_initial_location=preserve_location)
    else:
        # Chat mode: User/Agent conversation style using chat interface
        from agent.core_agent import LLMProvider

        # Convert string to enum
        if args.provider == "openai":
            provider = LLMProvider.OPENAI
        elif args.provider == "gemini":
            provider = LLMProvider.GEMINI
        elif args.provider == "lmstudio":
            provider = LLMProvider.LMSTUDIO
        else:
            provider = LLMProvider.OPENAI  # fallback

        chat_main(provider=provider, model=args.model, verbose=args.verbose)


if __name__ == "__main__":
    main()
