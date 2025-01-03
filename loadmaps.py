from osu import Client, BeatmapsetSearchFilter
import os
import json
from beatmap import Beatmap, Beatmap_Difficulty
from jsontools import Beatmap_To_Json

from dotenv import load_dotenv

load_dotenv()

api = Client.from_credentials(37144, os.getenv("app_secret"), None)

search_filter = BeatmapsetSearchFilter()
search_filter.set_nsfw(True)

def load_beatmapset(id):
    beatmap = api.get_beatmapset(id)
    
    diffs = []

    for i in beatmap.beatmaps:        
        difficulty = Beatmap_Difficulty(i.difficulty_rating, beatmap.id, i.id)
        diffs.append(difficulty)
        
    print(beatmap.status)
    
    loaded_beatmap = Beatmap(beatmap.id, beatmap.title, beatmap.artist, diffs, beatmap.creator, beatmap.status)
    
    return Beatmap_To_Json(loaded_beatmap)

def Json_to_Beatmap(json_data):
    diffs = []
    
    for i in json_data["difficulties"]:        
        difficulty = Beatmap_Difficulty(i["star_rating"], i["parent_id"], i["id"])
        diffs.append(difficulty)
        
    return Beatmap(json_data["id"], json_data["title"], json_data["artist"], diffs, json_data["mapper"], json_data["status"])

def load_object_indatabase(bmsobj):
    bms = None
    
    file = open("maps.json", "r")
    json_object = json.load(file)
    file.close()
    try:
        bms = json_object[str(bmsobj.id)]
    except:
        json_object[str(bmsobj.id)] = Beatmap_To_Json(bmsobj)
        file = open("maps.json", "w")
        json.dump(json_object, file)
        file.close()
    else:
        return 1
    
    return 0 

def loadnpage():
    file = open("bmpage.txt", "r")
    page = int(file.read())
    file.close()
    
    page += 1
    
    bms_page = api.search_beatmapsets(filters=search_filter, page=page)
    
    for i in bms_page.beatmapsets:
        diffs = []
    
        for y in i.beatmaps:
            diffs.append(Beatmap_Difficulty(y.difficulty_rating, y.beatmapset_id, y.id))
            
        mapset = Beatmap(i.id, i.title, i.artist, diffs, i.creator, i.status)
        
        load_object_indatabase(mapset)
        
        print(f"Mapset with ID {mapset.id} has been loaded")
        
        
    
    file = open("bmpage.txt", "w")
    file.write(str(page))
    file.close()