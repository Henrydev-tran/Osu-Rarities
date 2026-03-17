import time
from jsontools import return_json
import asyncio

start = time.perf_counter()
data = asyncio.run(return_json("json/maps.json"))
print(f"Loaded in {time.perf_counter() - start:.3f}s")

# This file is for testing the speed of loading maps and calculating probabilities, not used in the actual bot