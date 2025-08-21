#!/usr/bin/env python3
"""
Quick test script for path completion functionality.
"""

import sys
import os

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from input_handler.input_handler import enhanced_input, is_readline_available


def main():
    print("Testing path completion...")
    print(f"Readline available: {is_readline_available()}")
    print("Try typing a path and press Tab for completion.")
    print("Type 'exit' to quit.")

    while True:
        try:
            user_input = enhanced_input("test> ").strip()
            if user_input.lower() == "exit":
                break
            print(f"You entered: {user_input}")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break


if __name__ == "__main__":
    main()
