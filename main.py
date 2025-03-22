#!/usr/bin/env python3
import argparse
import sys
from ui.app import VoiceAssistantApp

def parse_arguments():
    """parse command line arguments."""
    parser = argparse.ArgumentParser(description="brother_eye")
    parser.add_argument("--model", default="gemma3:4b", help="model to use (default: gemma3:4b)")
    parser.add_argument("--system-prompt", help="system prompt to customize model's behavior")
    parser.add_argument("--prompt-file", help="file containing the system prompt")
    parser.add_argument("--wake-word", default="google", help="wake word to listen for (default: 'google')")

    args = parser.parse_args()

    if args.prompt_file:
        try:
            with open(args.prompt_file, 'r') as file:
                args.system_prompt = file.read().strip()
            print(f"loaded system prompt from {args.prompt_file}")
        except Exception as e:
            print(f"error loading prompt file: {e}")
            sys.exit(1)

    return args

def main():
    args = parse_arguments()

    app = VoiceAssistantApp(
        model=args.model,
        system_prompt=args.system_prompt,
        wake_word=args.wake_word
    )
    app.run()


if __name__ == "__main__":
    main()