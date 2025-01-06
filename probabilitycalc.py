import os
import json
from loadmaps import Dict_to_Beatmap
from jsontools import BeatmapDiff_To_Dict, BeatmapDiffNormalized_To_Dict
from beatmap import Beatmap_Difficulty_Normalized_Range
import random

def add_diffs_to_sorted_file():
    json_object = None
    
    file = open("maps.json", "r")
    json_object = json.load(file)
    file.close()
    
    maps = []
    
    for key in json_object:       
        loaded_json = json_object[key]
        
        beatmap = Dict_to_Beatmap(loaded_json)
        
        for i in beatmap.difficulties:
            maps.append(BeatmapDiff_To_Dict(i))
            
    file = open("sorteddiffs.json", "w")
    json.dump(maps, file)
    file.close()
    
def load_all_diffs():
    json_object = None
    
    file = open("sorteddiffs.json", "r")
    json_object = json.load(file)
    file.close()
    
    return json_object
    
def calculate_normalized_probabilities():
    maps = load_all_diffs()
    
    sum = 0
    
    normalized_maps = []
    
    for i in maps:
        difficulty = i["rarity"]
        sum += difficulty
        
    current_range = 0
        
    for y in maps:
        normalized_probability = y["rarity"]/sum
        
        beatmap = Beatmap_Difficulty_Normalized_Range(y["star_rating"], y["parent_id"], y["id"], y["title"], y["artist"], normalized_probability, current_range, y["rarity"])
        
        current_range += normalized_probability

        normalized_maps.append(beatmap)
        
    return normalized_maps
        
def add_normalized_diffs_to_sorted_file():
    object = calculate_normalized_probabilities()
    
    maps = []
    
    for i in object:
        maps.append(BeatmapDiffNormalized_To_Dict(i))
            
    file = open("sorteddiffs.json", "w")
    json.dump(maps, file)
    file.close()