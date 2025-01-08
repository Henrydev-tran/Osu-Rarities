from osu.asyncio import AsynchronousClient
from osu import Client, BeatmapsetSearchFilter
import os
import json
from beatmap import Beatmap, Beatmap_Difficulty
from jsontools import Beatmap_To_Json

from dotenv import load_dotenv

load_dotenv()

api = AsynchronousClient.from_credentials(37144, os.getenv("app_secret"), None)

search_filter = BeatmapsetSearchFilter()
search_filter.set_nsfw(True)

async def load_beatmapset(id):
    beatmap = await api.get_beatmapset(id)
    
    diffs = []

    for i in beatmap.beatmaps:        
        difficulty = Beatmap_Difficulty(i.difficulty_rating, beatmap.id, i.id, beatmap.title, beatmap.artist, i.version)
        diffs.append(difficulty)
    
    loaded_beatmap = Beatmap(beatmap.id, beatmap.title, beatmap.artist, diffs, beatmap.creator, beatmap.status)
    
    return await Beatmap_To_Json(loaded_beatmap)

async def Dict_to_Beatmap(dict_data):
    diffs = []
    
    for i in dict_data["difficulties"]:        
        difficulty = Beatmap_Difficulty(i["star_rating"], i["parent_id"], i["id"], i["title"], i["artist"], i["difficulty_name"])
        diffs.append(difficulty)
        
    return Beatmap(dict_data["id"], dict_data["title"], dict_data["artist"], diffs, dict_data["mapper"], dict_data["status"])

async def load_object_indatabase(bmsobj):
    bms = None
    
    file = open("json/maps.json", "r")
    json_object = json.load(file)
    file.close()
    try:
        bms = json_object[str(bmsobj.id)]
    except:
        json_object[str(bmsobj.id)] = await Beatmap_To_Json(bmsobj)
        file = open("json/maps.json", "w")
        json.dump(json_object, file)
        file.close()
    else:
        return 1
    
    return 0 

async def loadnpage():
    file = open("json/bmpage.count", "r")
    page = int(file.read())
    file.close()
    
    page += 1
    
    bms_page = await api.search_beatmapsets(page=page)
    
    for i in bms_page.beatmapsets:
        diffs = []
    
        for y in i.beatmaps:
            diffs.append(Beatmap_Difficulty(y.difficulty_rating, y.beatmapset_id, y.id, i.title, i.artist, y.version))
            
        mapset = Beatmap(i.id, i.title, i.artist, diffs, i.creator, i.status)
        
        await load_object_indatabase(mapset)
        
        print(f"Mapset with ID {mapset.id} has been loaded")
        
        
    
    file = open("json/bmpage.count", "w")
    file.write(str(page))
    file.close()