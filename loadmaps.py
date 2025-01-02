from ossapi import Ossapi
import os
from beatmap import Beatmap, Beatmap_Difficulty
import json
from jsontools import Beatmap_To_Json

from dotenv import load_dotenv

load_dotenv()

api = Ossapi(37144, os.getenv("app_secret"))

def load_beatmapset(id):
    beatmap = api.beatmapset(id)
    
    diffs = []

    for i in beatmap.beatmaps:        
        difficulty = Beatmap_Difficulty(i.difficulty_rating, beatmap.id, i.id)
        diffs.append(difficulty)
    
    loaded_beatmap = Beatmap(beatmap.id, beatmap.title, beatmap.artist, diffs, beatmap.creator)
    
    return Beatmap_To_Json(loaded_beatmap)