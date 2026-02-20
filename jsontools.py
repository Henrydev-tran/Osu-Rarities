from beatmap import *
import aiofiles
import json
from item import Shard, ShardCore, Special
import asyncio
import orjson
import pickle
import os

# Saves an object to a json path
async def save_to_json(path, obj):
    async with aiofiles.open(path, "w") as file:
        data = json.dumps(obj)   
        await file.write(data)
        
def build_maps(maps_json):
    return {
        k: Dict_to_Beatmap(v)
        for k, v in maps_json.items()
    }
        
# Returns an object from a json path
async def return_json(path):
    cache = path + ".pkl"

    if os.path.exists(cache):
        return await asyncio.to_thread(pickle.load, open(cache, "rb"))

    async with aiofiles.open(path, "rb") as f:
        raw = await f.read()

    data = await asyncio.to_thread(orjson.loads, raw)
    await asyncio.to_thread(pickle.dump, data, open(cache, "wb"))
    return data
    
# MapPool object that stores all the maps in json and Beatmap form
class MapPool:
    def __init__(self, maps={}, maps_json={}):
        self.maps = maps
        self.maps_json = maps_json
        
    async def load_from(self, file):
        self.maps_json = await return_json(file)

        # build all Beatmap objects off the event loop
        self.maps = await asyncio.to_thread(build_maps, self.maps_json)
            
    async def clear_all(self):
        self.maps = {}
        self.maps_json = {}
            
    async def save_to(self, file):
        await save_to_json(file, self.maps_json)

# Returns a Dict from a given Beatmap object
async def Beatmap_To_Json(beatmap):
    difficulties = []
    
    for i in beatmap.difficulties:
        difficulties.append({
            "id": i.id,
            "star_rating": i.sr,
            "parent_id": i.parent_id,
            "rarity": i.rarity,
            "title": i.title,
            "artist": i.artist,
            "difficulty_name": i.difficulty_name
        })
    
    result = {
        "id": beatmap.id,
        "title": beatmap.title,
        "artist": beatmap.artist,
        "difficulties": difficulties,
        "mapper": beatmap.mapper,
        "status": beatmap.status
    }
    
    return result

async def User_To_Dict(user):
    maps = []
    
    for i in user.maps:
        maps.append(await UBMO_To_Dict(i))
        
    items = {}
        
    for key1, val1 in user.items.items():
        for key2, val2 in val1.items():
            items.setdefault(key1, {})
            items[key1][key2] = await Item_To_Dict(val2)
    
    result = {
        "id": user.id,
        "maps": maps,
        "items": items,
        "pp": user.pp,
        "rolls_amount": user.rolls_amount,
        "rank": user.rank,
        "roll_max": user.roll_max,
        "luck_mult": user.luck_mult,
        "xp": user.xp,
        "level": user.level
    }
    
    return result

async def Dict_to_UBMD(dict):
    difficulty = User_BMD_Object(dict["star_rating"], dict["parent_id"], dict["id"], dict["title"], dict["artist"], dict["difficulty_name"], dict["duplicates"])
    
    return difficulty

# Returns a UBMO object from given dict
async def Dict_To_UBMO(data):
    diffs = []
    
    for i in data["difficulties"]:
        diffs.append(await Dict_to_UBMD(i))
    
    result = User_BM_Object(data["id"], data["title"], data["artist"], data["mapper"], data["status"], diffs)
    
    return result

# Returns a Dict from a given UBMO
async def UBMO_To_Dict(ubmo):
    result = {
        "id": ubmo.id,
        "title": ubmo.title,
        "artist": ubmo.artist,
        "difficulties": await ubmo.jsonify_diffs(),
        "mapper": ubmo.mapper,
        "status": ubmo.status
    }
    
    return result

async def Item_To_Dict(item):
    result = "Invalid Item"
    
    if item.type == "Shard":
        result = {
            "rarity": item.rarity,
            "cost": item.cost,
            "value": item.value,
            "name": item.name,
            "function": item.function,
            "id": item.id,
            "description": item.description,
            "duplicates": item.duplicates,
            "type": item.type,
            "shardrarity": item.shardrarity
        }
        
    
    if item.type == "ShardCore":
        result = {
            "rarity": item.rarity,
            "cost": item.cost,
            "value": item.value,
            "name": item.name,
            "function": item.function,
            "id": item.id,
            "description": item.description,
            "duplicates": item.duplicates,
            "type": item.type,
            "corerarity": item.corerarity
        }
        
    if item.type == "Special":
        result = {
            "rarity": item.rarity,
            "cost": item.cost,
            "value": item.value,
            "name": item.name,
            "function": item.function,
            "id": item.id,
            "description": item.description,
            "duplicates": item.duplicates,
            "type": item.type
        }
        
    return result
    
async def Dict_To_Item(item):
    result = "Invalid Item"
    
    if item["type"] == "Shard":
        result = Shard(item["rarity"], 
                       item["cost"], 
                       item["name"], 
                       item["value"], 
                       item["function"], 
                       item["id"], 
                       item["description"], 
                       item["duplicates"], 
                       item["type"], 
                       item["shardrarity"])
        
    if item["type"] == "ShardCore":
        result = ShardCore(item["rarity"], 
                       item["cost"], 
                       item["name"], 
                       item["value"], 
                       item["function"], 
                       item["id"], 
                       item["description"], 
                       item["duplicates"], 
                       item["type"], 
                       item["corerarity"])
        
    if item["type"] == "Special":
        result = Special(item["rarity"], 
                       item["cost"], 
                       item["name"], 
                       item["value"], 
                       item["function"], 
                       item["id"], 
                       item["description"], 
                       item["duplicates"], 
                       item["type"])
        
    return result

# There's definitely better ways to do this but cut me some slack
def UBMO_To_Dict_nonsync(ubmo):
    result = {
        "id": ubmo.id,
        "title": ubmo.title,
        "artist": ubmo.artist,
        "difficulties": ubmo.jsonify_diffs_nonsync(),
        "mapper": ubmo.mapper,
        "status": ubmo.status
    }
    
    return result

# Returns a Dict from a given Beatmap_Difficulty object
async def BeatmapDiff_To_Dict(beatmap):
    result = {
        "id": beatmap.id,
        "title": beatmap.title,
        "artist": beatmap.artist,
        "parent_id": beatmap.parent_id,
        "star_rating": beatmap.sr,
        "rarity": beatmap.rarity,
        "difficulty_name": beatmap.difficulty_name
    }
    
    return result

# Returns a Dict from a given UBMD object
async def UBMD_To_Dict(beatmap_d):
    result = {
        "id": beatmap_d.id,
        "title": beatmap_d.title,
        "artist": beatmap_d.artist,
        "parent_id": beatmap_d.parent_id,
        "star_rating": beatmap_d.sr,
        "rarity": beatmap_d.rarity,
        "difficulty_name": beatmap_d.difficulty_name,
        "duplicates": beatmap_d.duplicates
    }
    
    return result


# Returns a Dict from a given Beatmap_Difficulty_Cumulative_Range object
async def BeatmapDiffCumulative_To_Dict(beatmap):
    result = {
        "id": beatmap.id,
        "title": beatmap.title,
        "artist": beatmap.artist,
        "parent_id": beatmap.parent_id,
        "star_rating": beatmap.sr,
        "rarity": beatmap.rarity,
        "cumulative_probability": beatmap.cumulative_probability,
        "range": beatmap.range,
        "difficulty_name": beatmap.difficulty_name
    }
    
    return result

# Returns a Beatmap object with a given dict
def Dict_to_Beatmap(dict_data):
    diffs = [
        Beatmap_Difficulty(
            i["star_rating"],
            i["parent_id"],
            i["id"],
            i["title"],
            i["artist"],
            i["difficulty_name"],
        )
        for i in dict_data["difficulties"]
    ]
        
    return Beatmap(dict_data["id"], dict_data["title"], dict_data["artist"], diffs, dict_data["mapper"], dict_data["status"])

# Returns a Beatmap_Difficulty object with a given dict
async def Dict_to_BeatmapDiff(dict_data):
    difficulty = Beatmap_Difficulty(dict_data["star_rating"], dict_data["parent_id"], dict_data["id"], dict_data["title"], dict_data["artist"], dict_data["difficulty_name"])
    
    return difficulty