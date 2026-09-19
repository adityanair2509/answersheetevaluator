
import aiohttp
print(f"Aiohttp path: {aiohttp.__file__ if hasattr(aiohttp, '__file__') else 'No file attribute'}")
