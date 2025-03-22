import os
import json
from loadmaps import Dict_to_Beatmap
from jsontools import BeatmapDiff_To_Dict, BeatmapDiffNormalized_To_Dict
from beatmap import Beatmap_Difficulty_Normalized_Range
import random
import bisect

# Add all difficulties to sorted file for sorting
async def add_diffs_to_sorted_file():
    json_object = None
    
    file = open("json/maps.json", "r")
    json_object = json.load(file)
    file.close()
    
    maps = []
    
    for key in json_object:       
        loaded_json = json_object[key]
        
        beatmap = await Dict_to_Beatmap(loaded_json)
        
        for i in beatmap.difficulties:
            maps.append(await BeatmapDiff_To_Dict(i))
            
    file = open("json/sorteddiffs.json", "w")
    json.dump(maps, file)
    file.close()
    
# Returns all diffs in the sorted diffs file
async def load_all_diffs():
    json_object = None
    
    file = open("json/sorteddiffs.json", "r")
    json_object = json.load(file)
    file.close()
    
    return json_object

# Calculate all normalized probabilities for beatmaps
async def calculate_normalized_probabilities():
    maps = await load_all_diffs()
    
    sum = 0
    
    normalized_maps = []
    
    for i in maps:
        difficulty = 1/i["rarity"]
        sum += difficulty
        
    current_range = 0
        
    for y in maps:
        normalized_probability = (1/y["rarity"])/sum
        
        beatmap = Beatmap_Difficulty_Normalized_Range(y["star_rating"], y["parent_id"], y["id"], y["title"], y["artist"], '%.25f' % normalized_probability, current_range, y["rarity"], y["difficulty_name"])
        
        current_range += normalized_probability

        normalized_maps.append(beatmap)
        
    return normalized_maps
    
# Normalize all ranges in file (uses calculate_normalized_probabilities)
async def add_normalized_diffs_to_sorted_file():
    object = await calculate_normalized_probabilities()
    
    maps = []
    
    for i in object:
        maps.append(await BeatmapDiffNormalized_To_Dict(i))
            
    file = open("json/sorteddiffs.json", "w")
    json.dump(maps, file)
    file.close()
    
    return maps

# Add all calculated ranges to ranges file
async def add_ranges_to_file():
    norm_diffs = await load_all_diffs()
    
    ranges = []

    for i in norm_diffs:
        ranges.append('%.25f' % i["range"])
    
    file = open("json/ranges.json", "w")
    json.dump(ranges, file)
    file.close()
    
    return ranges

# Returns the amount of loaded beatmaps
async def get_amount_beatmaps():
    file = open("json/sorteddiffs.json", "r")
    json_object = json.load(file)
    file.close()
    
    return len(json_object)

# Returns the ranges of calculated diffs
async def get_ranges():
    ranges = None
    
    file = open("json/ranges.json", "r")
    ranges = json.load(file)
    file.close()
    
    return ranges

# Returns a random index
async def get_random_index():
    random_number = '%.25f' % random.random()
    
    ranges = await get_ranges()
    
    index = bisect.bisect_left(ranges, random_number)
    
    return index

# Returns a random beatmap (uses get_random_index)
async def get_random_map():
    random_index = await get_random_index()
    
    maps = await load_all_diffs()
    
    return maps[random_index]