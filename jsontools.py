import json
from beatmap import *

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
    result = {
        "id": user.id,
        "maps": user.maps,
        "mappers": user.mappers,
        "items": user.items,
        "pp": user.pp,
        "rolls_amount": user.rolls_amount,
        "rank": user.rank
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