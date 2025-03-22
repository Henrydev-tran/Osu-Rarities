from osu import AsynchronousClient, BeatmapsetSearchFilter
import os
import json
from beatmap import Beatmap, Beatmap_Difficulty
from jsontools import Beatmap_To_Json
import asyncio

from dotenv import load_dotenv

load_dotenv()

# Initialize API
api = AsynchronousClient.from_credentials(37144, os.getenv("app_secret"), None)

search_filter = BeatmapsetSearchFilter()

# Unused RankStatus to Integer function
"""async def Status_to_Int(status):
    if status == RankStatus.RANKED:
        return 1
    if status == RankStatus.LOVED:
        return 4
    if status == RankStatus.APPROVED:
        return 2
    if status == RankStatus.GRAVEYARD:
        return -2
    if status == RankStatus.PENDING:
        return 0
    if status == RankStatus.QUALIFIED:
        return 3
    if status == RankStatus.WIP:
        return -1"""

# Load a beatmapset with a given ID
async def load_beatmapset(id):
    beatmap = await api.get_beatmapset(id)
    
    diffs = []

    for i in beatmap.beatmaps:        
        difficulty = Beatmap_Difficulty(i.difficulty_rating, beatmap.id, i.id, beatmap.title, beatmap.artist, i.version)
        diffs.append(difficulty)
    
    loaded_beatmap = Beatmap(beatmap.id, beatmap.title, beatmap.artist, diffs, beatmap.creator, beatmap.status)
    
    return await Beatmap_To_Json(loaded_beatmap)

# Returns a Beatmap object with a given dict
async def Dict_to_Beatmap(dict_data):
    diffs = []
    
    for i in dict_data["difficulties"]:        
        difficulty = Beatmap_Difficulty(i["star_rating"], i["parent_id"], i["id"], i["title"], i["artist"], i["difficulty_name"])
        diffs.append(difficulty)
        
    return Beatmap(dict_data["id"], dict_data["title"], dict_data["artist"], diffs, dict_data["mapper"], dict_data["status"])

# Load a Beatmap object into the database, returns 1 if map already loaded, 0 if map loaded success
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

# Load the next page of beatmapsets
async def loadnpage():
    file = open("json/bmpage.count", "r")
    page = int(file.read())
    file.close()
    
    page += 1
    
    bms_page = await api.search_beatmapsets(page=page)
    
    print(bms_page)
    
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

# Unfinished function, will loop through all pages of a certain year and load all beatmaps
async def loadALL(page):
    maps = await api.search_beatmapsets(filters=search_filter, page=page)
    mapsets = []
    
    for i in maps.beatmapsets:
        diffs = []
        
        for y in i.beatmaps:
            diffs.append(Beatmap_Difficulty(y.difficulty_rating, i.id, y.id, i.title, i.artist, y.version))
        
        mapsets.append(await Beatmap_To_Json(Beatmap(i.id, i.title, i.artist, diffs, i.creator, i.status)))
    
    file = open("test.txt", "w")
    json.dump(mapsets, file)
    file.close()
    
    
"""async def loadmaps():
    

print(asyncio.run(loadALL()))"""