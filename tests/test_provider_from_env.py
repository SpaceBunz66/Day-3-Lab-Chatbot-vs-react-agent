import os
import sys

from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.provider_factory import create_provider_from_env


def test_provider_from_env():
    load_dotenv()

    provider = create_provider_from_env()

    prompt = "Explain what an AI Agent is in one sentence."
    print(f"--- Provider selected: {provider.__class__.__name__} ---")
    print(f"Model: {provider.model_name}")
    print(f"\nUser: {prompt}")
    print("Assistant: ", end="", flush=True)

    try:
        for chunk in provider.stream(prompt):
            print(chunk, end="", flush=True)
        print("\n\n✅ Provider from .env works correctly!")
    except Exception as exc:
        print(f"\n❌ Error during execution: {exc}")


if __name__ == "__main__":
    test_provider_from_env()
