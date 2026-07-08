"""scripts/check_api_key.py — quick sanity check for the Vision API key."""
import sys
sys.path.insert(0, ".")

import httpx
import base64

from packages.common.config import get_settings

s = get_settings()
key = s.google_vision_api_key

if not key:
    print("ERROR: GOOGLE_VISION_API_KEY not set in .env")
    sys.exit(1)

print(f"Key loaded: ...{key[-8:]}")

# Minimal 1x1 white PNG — cheapest possible API call
tiny_png = bytes([
    0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a,0x00,0x00,0x00,0x0d,0x49,0x48,0x44,0x52,
    0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,0x08,0x02,0x00,0x00,0x00,0x90,0x77,0x53,
    0xde,0x00,0x00,0x00,0x0c,0x49,0x44,0x41,0x54,0x08,0xd7,0x63,0xf8,0xcf,0xc0,0x00,
    0x00,0x00,0x02,0x00,0x01,0xe2,0x21,0xbc,0x33,0x00,0x00,0x00,0x00,0x49,0x45,0x4e,
    0x44,0xae,0x42,0x60,0x82,
])
b64 = base64.b64encode(tiny_png).decode()

resp = httpx.post(
    "https://vision.googleapis.com/v1/images:annotate",
    params={"key": key},
    json={
        "requests": [
            {
                "image": {"content": b64},
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    },
    timeout=15,
)

print(f"HTTP status: {resp.status_code}")
data = resp.json()
err = data.get("responses", [{}])[0].get("error", {})
if err:
    code = err.get("code", "?")
    msg  = err.get("message", "")
    print(f"API error {code}: {msg[:200]}")
    if code == 403 and "billing" in msg.lower():
        print()
        print("  --> This API key belongs to a Google Cloud project that")
        print("      does NOT have billing enabled.")
        print("      Enable billing at: https://console.cloud.google.com/billing")
        print("      The Vision API has a free quota (1000 calls/month) BUT")
        print("      only when billing is enabled on the project.")
else:
    print("API call SUCCEEDED — key is valid and billing is active!")
    resp_body = data.get("responses", [{}])[0]
    print("Response fields:", list(resp_body.keys()))
