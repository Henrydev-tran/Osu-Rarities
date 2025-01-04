import json

def Beatmap_To_Json(beatmap):
    difficulties = []
    
    for i in beatmap.difficulties:
        difficulties.append({
            "id": i.id,
            "star_rating": i.sr,
            "parent_id": i.parent_id,
            "rarity": i.rarity,
            "title": i.title,
            "artist": i.artist
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

def BeatmapDiff_To_Dict(beatmap):
    result = {
        "id": beatmap.id,
        "title": beatmap.title,
        "artist": beatmap.artist,
        "parent_id": beatmap.parent_id,
        "star_rating": beatmap.sr,
        "rarity": beatmap.rarity
    }
    
    return result