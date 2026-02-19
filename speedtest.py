import time
from jsontools import return_json
import asyncio

start = time.perf_counter()
data = asyncio.run(return_json("json/maps.json"))
print(f"Loaded in {time.perf_counter() - start:.3f}s")