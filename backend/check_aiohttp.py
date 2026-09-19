
import aiohttp
print(f"aiohttp version: {aiohttp.__version__}")
print(f"aiohttp file: {aiohttp.__file__}")
try:
    session = aiohttp.ClientSession()
    print("ClientSession found and accessible")
except Exception as e:
    print(f"Error accessing ClientSession: {e}")
