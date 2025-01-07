import os
import json
from loadmaps import Dict_to_Beatmap
from jsontools import BeatmapDiff_To_Dict, BeatmapDiffNormalized_To_Dict
from beatmap import Beatmap_Difficulty_Normalized_Range
import random
import bisect

async def add_diffs_to_sorted_file():
    json_object = None
    
    file = open("maps.json", "r")
    json_object = json.load(file)
    file.close()
    
    maps = []
    
    for key in json_object:       
        loaded_json = json_object[key]
        
        beatmap = await Dict_to_Beatmap(loaded_json)
        
        for i in beatmap.difficulties:
            maps.append(await BeatmapDiff_To_Dict(i))
            
    file = open("sorteddiffs.json", "w")
    json.dump(maps, file)
    file.close()
    
async def load_all_diffs():
    json_object = None
    
    file = open("sorteddiffs.json", "r")
    json_object = json.load(file)
    file.close()
    
    return json_object
    
async def calculate_normalized_probabilities():
    maps = await load_all_diffs()
    
    sum = 0
    
    normalized_maps = []
    
    for i in maps:
        difficulty = 1/i["rarity"]
        sum += difficulty
        
    current_range = 0
        
    for y in maps:
        print(y["rarity"])
        normalized_probability = (1/y["rarity"])/sum
        
        beatmap = Beatmap_Difficulty_Normalized_Range(y["star_rating"], y["parent_id"], y["id"], y["title"], y["artist"], '%.20f' % normalized_probability, current_range, y["rarity"], y["difficulty_name"])
        
        current_range += normalized_probability

        normalized_maps.append(beatmap)
        
    return normalized_maps
        
async def add_normalized_diffs_to_sorted_file():
    object = await calculate_normalized_probabilities()
    
    maps = []
    
    for i in object:
        maps.append(await BeatmapDiffNormalized_To_Dict(i))
            
    file = open("sorteddiffs.json", "w")
    json.dump(maps, file)
    file.close()
    
    return maps

async def get_normalized_diffs():
    json_obj = None
    
    file = open("sorteddiffs.json", "r")
    json_obj = json.load(file)
    file.close()
    
    return json_obj
    
async def add_ranges_to_file():
    norm_diffs = await get_normalized_diffs()
    
    ranges = []

    for i in norm_diffs:
        ranges.append('%.20f' % i["range"])
    
    file = open("ranges.json", "w")
    json.dump(ranges, file)
    file.close()
    
    return ranges

async def get_amount_beatmaps():
    file = open("sorteddiffs.json", "r")
    json_object = json.load(file)
    file.close()
    
    return len(json_object)

async def get_ranges():
    ranges = None
    
    file = open("ranges.json", "r")
    ranges = json.load(file)
    file.close()
    
    return ranges

async def get_random_index():
    random_number = '%.20f' % random.random()
    
    ranges = await get_ranges()
    
    index = bisect.bisect_left(ranges, random_number)
    
    return index

async def get_random_map():
    random_index = await get_random_index()
    
    maps = await get_normalized_diffs()
    
    print(random_index)
    print(await get_amount_beatmaps())
    
    return maps[random_index]