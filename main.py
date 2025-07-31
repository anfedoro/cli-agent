import argparse

from agent import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM Terminal Agent")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed token usage information")
    args = parser.parse_args()

    main(verbose=args.verbose)
