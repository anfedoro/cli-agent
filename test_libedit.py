#!/usr/bin/env python3
"""
Test libedit completion
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import readline

    def test_completer(text, state):
        print(f"\nCOMPLETER: text='{text}', state={state}")
        import glob

        matches = glob.glob(text + "*")
        matches = [m + "/" if os.path.isdir(m) else m for m in matches]
        matches.sort()
        try:
            return matches[state]
        except IndexError:
            return None

    print(f"Backend: {getattr(readline, '__doc__', 'Unknown')}")

    readline.set_completer(test_completer)

    # Configure for libedit
    if "libedit" in getattr(readline, "__doc__", "").lower():
        print("Using libedit configuration...")
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        print("Using GNU readline configuration...")
        readline.parse_and_bind("tab: complete")

    print("Test: type './' and press Tab")

    while True:
        try:
            line = input("test> ")
            if line.strip().lower() == "quit":
                break
            print(f"Input: {line}")
        except (KeyboardInterrupt, EOFError):
            break

except ImportError:
    print("readline not available")
