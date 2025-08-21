import argparse

from interface.chat_interface import chat_main
from interface.shell_interface import shell_main


def main():
    """Main entry point for the CLI agent."""
    parser = argparse.ArgumentParser(description="LLM Terminal Agent")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed token usage information")
    parser.add_argument("--provider", "-p", choices=["openai", "gemini", "lmstudio"], default="openai", help="LLM provider to use (default: openai)")
    parser.add_argument("--model", "-m", help="Model to use for the selected provider")
    parser.add_argument("--no-reasoning", action="store_true", help="Disable reasoning process for faster responses (LM Studio)")
    parser.add_argument("--mode", choices=["chat", "shell"], default="chat", help="Run mode: chat (conversation) or shell (command mode)")
    parser.add_argument("--trace", "-t", action="store_true", help="Enable trace mode (show LLM execution details, only in shell mode)")
    args = parser.parse_args()

    if args.mode == "shell":
        # Shell mode: standard shell prompt with intelligent routing
        shell_main(provider=args.provider, model=args.model, trace=args.trace or args.verbose)
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
