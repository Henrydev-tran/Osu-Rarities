import os
import json
from loadmaps import Dict_to_Beatmap
from jsontools import *
from beatmap import Beatmap_Difficulty_Cumulative_Range
import random
import bisect
import asyncio
import aiofiles

# Stored maps and ranges variable for optimization (less file access)
maps = None
ranges = None

total_weight = 0

with open("json/total_weight.count", "r") as file:
    total_weight = int(file.read())


max_probability_scale = 1_000_000_000_000

# Add all difficulties to sorted file for sorting
async def add_diffs_to_sorted_file():
    json_object = await return_json("json/maps.json")
    
    maps = []
    
    for key in json_object:       
        loaded_json = json_object[key]
        
        beatmap = Dict_to_Beatmap(loaded_json)
        
        for i in beatmap.difficulties:
            maps.append(await BeatmapDiff_To_Dict(i))
            
    await save_to_json("json/sorteddiffs.json", maps)
    
# Returns all diffs in the sorted diffs file
async def load_all_diffs():
    json_object = await return_json("json/sorteddiffs.json")
    
    return json_object

# Calculate all cumulative probabilities for beatmaps
async def calculate_cumulative_probabilities():
    global total_weight

    maps = await load_all_diffs()
    
    total_weight = 0
    
    rarity_weights = []
    
    calculated_maps = []
    
    for i in maps:
        rarity_weights.append(max_probability_scale // i["rarity"])
        
    current_range = 0
    
    num = 0
    
    for y in maps:
        current_range += rarity_weights[num]
        total_weight += rarity_weights[num]
        
        beatmap = Beatmap_Difficulty_Cumulative_Range(y["star_rating"], y["parent_id"], y["id"], y["title"], y["artist"], rarity_weights[num], current_range, y["rarity"], y["difficulty_name"])
        
        calculated_maps.append(beatmap)
        
        num += 1
        
    async with aiofiles.open("json/total_weight.count", "w") as file:
        await file.write(str(total_weight))
        
    return calculated_maps
        
# Normalize all ranges in file (uses calculate_cumulative_probabilities)
async def add_cumulative_diffs_to_sorted_file():
    object = await calculate_cumulative_probabilities()
    
    maps = []
    
    for i in object:
        maps.append(await BeatmapDiffCumulative_To_Dict(i))
            
    await save_to_json("json/sorteddiffs.json", maps)
    
    return maps

# Add all calculated ranges to ranges file
async def add_ranges_to_file():
    norm_diffs = await load_all_diffs()
    
    ranges = []

    for i in norm_diffs:
        ranges.append(i["range"])
    
    await save_to_json("json/ranges.json", ranges)
    
    return ranges

# Update the maps/ranges variable
async def update_optimization_variables():
    global maps
    global ranges
    global total_weight
    
    maps = await load_all_diffs()
    ranges = await get_ranges()
    
    async with aiofiles.open("json/total_weight.count", "r") as file:
        total_weight = int(await file.read())

# Returns the amount of loaded beatmaps
async def get_amount_beatmaps():
    json_object = await return_json("json/sorteddiffs.json")
    
    return len(json_object)

# Returns the ranges of calculated diffs
async def get_ranges():
    ranges = await return_json("json/ranges.json")
    
    return ranges

# Returns a random index
async def get_random_index():
    global ranges
    
    random_number = random.randint(1, total_weight)
    
    index = bisect.bisect_left(ranges, random_number)
    
    return index

# Returns a random beatmap (uses get_random_index)
async def get_random_map():
    global maps
    
    random_index = await get_random_index()
    
    maps_obj = maps
    
    return maps_obj[random_index]


maps = asyncio.run(load_all_diffs())
ranges = asyncio.run(get_ranges())