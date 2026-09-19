
import os
from packages.common.config import get_settings
from google import genai
import json

def run_diagnostic():
    print("--- ScribeScore Gemini Diagnostic ---")

    settings = get_settings()

    # 1. Check Env Var
    api_key = settings.gemini_api_key
    if api_key:
        print(f"[✓] GEMINI_API_KEY is SET (Length: {len(api_key)})")
    else:
        print("[✗] GEMINI_API_KEY is NOT SET")
        return

    # 2. Check Demo Mode
    print(f"Demo Mode: {settings.demo_mode}")

    # 3. Test Connection
    print("\nTesting Connection to Gemini API...")
    try:
        client = genai.Client(api_key=api_key)
        model_name = "gemini-2.5-flash"
        print(f"Trying model: {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'Connection Successful'"
        )
        if response and response.text:
            print(f"[✓] API Connection SUCCESS with {model_name}: {response.text.strip()}")
        else:
            print("[✗] API Connection FAILED: Empty response")
    except Exception as e:
        print(f"[✗] API Connection ERROR: {str(e)}")

if __name__ == '__main__':
    try:
        run_diagnostic()
    except Exception as e:
        print(f"Fatal Diagnostic Error: {e}")
