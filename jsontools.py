from beatmap import *
import aiofiles
import json

# Saves an object to a json path
async def save_to_json(path, obj):
    async with aiofiles.open(path, "w") as file:
        data = json.dumps(obj)   
        await file.write(data)
        
# Returns an object from a json path
async def return_json(path):
    async with aiofiles.open(path, "r") as file:
        contents = await file.read()
        return json.loads(contents)
    
# MapPool object that stores all the maps in json and Beatmap form
class MapPool:
    def __init__(self, maps={}, maps_json={}):
        self.maps = maps
        self.maps_json = maps_json
        
    async def load_from(self, file):
        self.maps_json = await return_json(file)
        
        for i in self.maps_json:
            self.maps[i] = await Dict_to_Beatmap(self.maps_json[i])
            
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
    
    result = {
        "id": user.id,
        "maps": maps,
        "mappers": user.mappers,
        "items": user.items,
        "pp": user.pp,
        "rolls_amount": user.rolls_amount,
        "rank": user.rank,
        "roll_max": user.roll_max
    }
    
    return result

async def Dict_to_UBMD(dict):
    difficulty = User_BMD_Object(dict["sr"], dict["parent_id"], dict["id"], dict["title"], dict["artist"], dict["diff_name"], dict["duplicates"])
    
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
async def Dict_to_Beatmap(dict_data):
    diffs = []
    
    for i in dict_data["difficulties"]:        
        difficulty = Beatmap_Difficulty(i["star_rating"], i["parent_id"], i["id"], i["title"], i["artist"], i["difficulty_name"])
        diffs.append(difficulty)
        
    return Beatmap(dict_data["id"], dict_data["title"], dict_data["artist"], diffs, dict_data["mapper"], dict_data["status"])

# Returns a Beatmap_Difficulty object with a given dict
async def Dict_to_BeatmapDiff(dict_data):
    difficulty = Beatmap_Difficulty(dict_data["star_rating"], dict_data["parent_id"], dict_data["id"], dict_data["title"], dict_data["artist"], dict_data["difficulty_name"])
    
    return difficulty