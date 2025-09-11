from osu import AsynchronousClient, BeatmapsetSearchFilter
import os
from beatmap import Beatmap, Beatmap_Difficulty, User_BM_Object
from jsontools import *
import aiofiles

from dotenv import load_dotenv

load_dotenv()

# Initialize API
api = AsynchronousClient.from_credentials(37144, os.getenv("app_secret"), None)

with open("json/year.count", "r") as file:
    query_year = int(file.read())

maps = MapPool()

search_filter = BeatmapsetSearchFilter()

search_filter.set_query(f"updated={str(query_year)}")

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
        
# Update the global maps variable
async def load_gmaps_variable():
    global maps
    
    await maps.load_from("json/maps.json")
    
    return maps.maps

# Returns a UBMO object from a given ID
async def find_beatmap(id):
    global maps
    
    map = maps.maps[str(id)]
    
    ubmo = User_BM_Object(id, map.title, map.artist, map.mapper, map.status)
    
    return ubmo
        
# Get the year from year.count file
async def get_year():
    async with aiofiles.open("json/year.count", "r") as file:
        y = int(await file.read())
    
    return y

# Change the year from year.count file
async def change_year(year):
    async with aiofiles.open("json/year.count", "w") as file:
        await file.write(str(year))
    
    return year

# Change search query to specific year
async def set_query_year(year):
    search_filter.set_query(f"updated={str(year)}")
    
    return year

# Load a beatmapset with a given ID
async def load_beatmapset(id):
    beatmap = await api.get_beatmapset(id)
    
    diffs = []

    for i in beatmap.beatmaps:        
        difficulty = Beatmap_Difficulty(i.difficulty_rating, beatmap.id, i.id, beatmap.title, beatmap.artist, i.version)
        diffs.append(difficulty)
    
    loaded_beatmap = Beatmap(beatmap.id, beatmap.title, beatmap.artist, diffs, beatmap.creator, beatmap.status)
    
    return await Beatmap_To_Json(loaded_beatmap)

# Load a Beatmap object into the database, returns 1 if map already loaded, 0 if map loaded success
async def load_object_indatabase(bmsobj):
    bms = None
    json_object = await return_json("json/maps.json")
    
    try:
        bms = json_object[str(bmsobj.id)]
    except:
        json_object[str(bmsobj.id)] = await Beatmap_To_Json(bmsobj)
        await save_to_json("json/maps.json", json_object)
    else:
        return 1
    
    return 0 

# Load the next page of beatmapsets
async def loadnpage():
    async with aiofiles.open("json/bmpage.count", "r") as file:
        page = int(await file.read())
    
    page += 1
    
    bms_page = await api.search_beatmapsets(filters=search_filter, page=page)
    
    print(bms_page)
    
    if len(bms_page.beatmapsets) == 0:
        return 0
    
    json_object = await return_json("json/maps.json")
    
    for i in bms_page.beatmapsets:
        
        diffs = []
    
        for y in i.beatmaps:
            diffs.append(Beatmap_Difficulty(y.difficulty_rating, y.beatmapset_id, y.id, i.title, i.artist, y.version))
            
        mapset = Beatmap(i.id, i.title, i.artist, diffs, i.creator, i.status)
        
        json_object[str(mapset.id)] = await Beatmap_To_Json(mapset)
        
        print(f"Mapset with ID {mapset.id} has been loaded")
    
    await save_to_json("json/maps.json", maps)
    
    async with aiofiles.open("json/bmpage.count", "w") as file:
        await file.write(str(page))
    
    return 1
   
# Set the page count back to 0 
async def reset_page_count():
    async with aiofiles.open("json/bmpage.count", "w") as file:
        await file.write("0")
    
# Set the page count
async def set_page_count(page):
    async with aiofiles.open("json/bmpage.count", "w") as file:
        await file.write(str(page))

# Unused function, will loop through all pages of a certain year and load all beatmaps
async def loadALL():
    while True:
        result = await loadnpage()
        
        if result == 0:
            print("out of beatmaps, starting next year")
            
            await set_page_count(0)
            await change_year(await get_year() + 1)
            await set_query_year(await get_year())