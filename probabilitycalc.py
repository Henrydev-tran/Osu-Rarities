import os
import json
from loadmaps import Dict_to_Beatmap
from jsontools import BeatmapDiff_To_Dict

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

add_diffs_to_sorted_file()