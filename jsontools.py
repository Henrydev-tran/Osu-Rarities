import json

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
    pass

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