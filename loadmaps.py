from ossapi import Ossapi
from ossapi.enums import RankStatus
import os
from beatmap import Beatmap, Beatmap_Difficulty
import json
from jsontools import Beatmap_To_Json

from dotenv import load_dotenv

load_dotenv()

api = Ossapi(37144, os.getenv("app_secret"))

def Status_to_Int(status):
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
        return -1

def load_beatmapset(id):
    beatmap = api.beatmapset(id)
    
    diffs = []

    for i in beatmap.beatmaps:        
        difficulty = Beatmap_Difficulty(i.difficulty_rating, beatmap.id, i.id)
        diffs.append(difficulty)
        
    print(beatmap.status)
    
    loaded_beatmap = Beatmap(beatmap.id, beatmap.title, beatmap.artist, diffs, beatmap.creator, Status_to_Int(beatmap.status))
    
    return Beatmap_To_Json(loaded_beatmap)
