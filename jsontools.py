import json

def Beatmap_To_Json(beatmap):
    difficulties = []
    
    for i in beatmap.difficulties:
        difficulties.append({
            "id": i.id,
            "star_rating": i.sr,
            "parent_id": i.parent_id,
            "rarity": i.rarity
        })
    
    result = {
        "id": beatmap.id,
        "title": beatmap.title,
        "artist": beatmap.artist,
        "difficulties": difficulties,
        "mapper": beatmap.mapper
    }
    
    return json.dumps(result)