import argparse

from agent import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM Terminal Agent")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed token usage information")
    parser.add_argument("--provider", "-p", choices=["openai", "gemini", "lmstudio"], default="openai", help="LLM provider to use (default: openai)")
    parser.add_argument("--model", "-m", help="Model to use for the selected provider")
    parser.add_argument("--no-reasoning", action="store_true", help="Disable reasoning process for faster responses (LM Studio)")
    args = parser.parse_args()

    main(verbose=args.verbose, provider=args.provider, model=args.model, no_reasoning=args.no_reasoning)
