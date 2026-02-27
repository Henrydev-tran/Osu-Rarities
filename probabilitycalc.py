from loadmaps import Dict_to_Beatmap
from jsontools import *
from beatmap import Beatmap_Difficulty_Cumulative_Range
import random
import bisect
import asyncio
import aiofiles
import os
import time

# Stored maps and ranges variable for optimization (less file access)
maps = None

max_probability_scale = 1_000_000_000_000

luck_tables = {}

async def preload_all_luck_tables():
    base_dir = "json/luck_tables"

    if not os.path.exists(base_dir):
        return

    for folder in os.listdir(base_dir):
        # folder name like "luck_4x"
        if not folder.startswith("luck_") or not folder.endswith("x"):
            continue

        luck_str = folder.removeprefix("luck_").removesuffix("x")

        try:
            luck = float(luck_str)
        except ValueError:
            continue

        ranges_path = f"{base_dir}/{folder}/ranges.json"
        weight_path = f"{base_dir}/{folder}/total_weight.count"

        if not os.path.exists(ranges_path) or not os.path.exists(weight_path):
            continue

        ranges = await return_json(ranges_path)

        async with aiofiles.open(weight_path, "r") as f:
            total_weight = int(await f.read())

        luck_tables[luck] = (ranges, total_weight)

    print(f"Loaded {len(luck_tables)} luck tables into memory")

async def preload_single_luck(luck: float):
    base_path = f"json/luck_tables/luck_{luck}x"

    ranges_path = f"{base_path}/ranges.json"
    weight_path = f"{base_path}/total_weight.count"

    if not os.path.exists(ranges_path) or not os.path.exists(weight_path):
        raise FileNotFoundError(f"Luck table {luck}x does not exist")

    ranges = await return_json(ranges_path)

    async with aiofiles.open(weight_path, "r") as f:
        total_weight = int(await f.read())

    luck_tables[luck] = (ranges, total_weight)

async def build_luck_table(luck: float):
    global maps
    
    base_path = f"json/luck_tables/luck_{luck}x"
    os.makedirs(base_path, exist_ok=True)

    sorted_maps = maps

    ranges = []
    total_weight = 0
    current_range = 0

    for m in sorted_maps:
        rarity = m["rarity"]

        if rarity >= luck:
            # rarer than pivot → make more common
            effective_rarity = rarity / luck
        else:
            # more common than pivot → make rarer
            effective_rarity = rarity * luck

        weight = max(1, int(max_probability_scale // effective_rarity))

        total_weight += weight
        current_range += weight
        ranges.append(current_range)

    await save_to_json(f"{base_path}/ranges.json", ranges)

    async with aiofiles.open(f"{base_path}/total_weight.count", "w") as f:
        await f.write(str(total_weight))

# Add all difficulties to sorted file for sorting
async def add_diffs_to_sorted_file():
    json_object = await return_json("json/maps.json")
    
    sorted_maps = []
    
    for key in json_object:       
        loaded_json = json_object[key]
        
        beatmap = await Dict_to_Beatmap(loaded_json)
        
        for i in beatmap.difficulties:
            sorted_maps.append(await BeatmapDiff_To_Dict(i))
            
    await save_to_json("json/sorteddiffs.json", sorted_maps)
    
# Returns all diffs in the sorted diffs file
async def load_all_diffs():
    json_object = await return_json("json/sorteddiffs.json")
    
    return json_object

# Calculate all cumulative probabilities for beatmaps
"""async def calculate_cumulative_probabilities():
    global total_weight, maps

    sorted_maps = await load_all_diffs()
    
    total_weight = 0
    
    rarity_weights = []
    
    calculated_maps = []
    
    for i in maps:
        rarity_weights.append(max_probability_scale // i["rarity"])
        
    current_range = 0
    
    num = 0
    
    for y in sorted_maps:
        current_range += rarity_weights[num]
        total_weight += rarity_weights[num]
        
        beatmap = Beatmap_Difficulty_Cumulative_Range(y["star_rating"], y["parent_id"], y["id"], y["title"], y["artist"], rarity_weights[num], current_range, y["rarity"], y["difficulty_name"])
        
        calculated_maps.append(beatmap)
        
        num += 1
        
    async with aiofiles.open("json/total_weight.count", "w") as file:
        await file.write(str(total_weight))
        
    return calculated_maps"""
        
# Normalize all ranges in file (uses calculate_cumulative_probabilities)
"""async def add_cumulative_diffs_to_sorted_file():
    object = await calculate_cumulative_probabilities()
    
    sorted_maps = []
    
    for i in object:
        sorted_maps.append(await BeatmapDiffCumulative_To_Dict(i))
            
    await save_to_json("json/sorteddiffs.json", sorted_maps)
    
    return sorted_maps"""

# Add all calculated ranges to ranges file
"""async def add_ranges_to_file():
    norm_diffs = await load_all_diffs()
    
    sorted_ranges = []

    for i in norm_diffs:
        sorted_ranges.append(i["range"])
    
    await save_to_json("json/ranges.json", sorted_ranges)
    
    return sorted_ranges"""

# Update the maps/ranges variable
async def update_optimization_variables():
    global maps
    
    maps = await load_all_diffs()
    await preload_all_luck_tables()

# Returns the amount of loaded beatmaps
async def get_amount_beatmaps():
    json_object = await return_json("json/sorteddiffs.json")
    
    return len(json_object)

# Returns the ranges of calculated diffs
"""async def get_ranges():
    ranges = await return_json("json/ranges.json")
    
    return ranges"""

# Returns a random index
async def get_random_index(luck: float):
    if luck not in luck_tables:
        await build_luck_table(luck)
        await preload_single_luck(luck)

    ranges, total_weight = luck_tables[luck]

    roll = random.randint(1, total_weight)
    return bisect.bisect_left(ranges, roll)

# Returns a random beatmap (uses get_random_index)
async def get_random_map(luck: float = 1.0):
    global maps 
    
    index = await get_random_index(luck)
    return maps[index]

async def init_probabilitycalc():
    global maps
    start = time.perf_counter()
    maps = await load_all_diffs()
    await preload_all_luck_tables()
    print(f"Loaded lucktables in {time.perf_counter() - start:.3f}s")