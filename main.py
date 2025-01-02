import os
import random
import copy
import json

import discord
from discord.ext import commands

from dotenv import load_dotenv

load_dotenv()

from raritycalculation import Calculate_Rarity
from jsontools import Beatmap_To_Json
from loadmaps import *

client = commands.Bot(command_prefix='o!', intents=discord.Intents(messages=True, guilds=True, message_content=True))

@client.command('ping')
async def ping(ctx):
    await ctx.message.reply("hi")

@client.command("calculaterarity")
async def calcrare(ctx, sr):
    await ctx.message.reply(f"The given star rating of {sr} has a rarity of 1 in {round(Calculate_Rarity(sr))}")
    
@client.command("load_beatmapset")
async def loadbms(ctx, bms):
    await ctx.message.reply(load_beatmapset(bms))
    
@client.command("loadbms_intodatabase")
async def loadbmsintodatabase(ctx, msid):
    bms = None
    
    json_object = None
    
    file = open("maps.json", "r")
    json_object = json.load(file)
    file.close()
    
    try:
        bms = json.loads(json_object[str(msid)])
        print(bms)
    except:
        json_object[str(msid)] = json.dumps(load_beatmapset(msid))
        file = open("maps.json", "w")
        json.dump(json_object, file)
        file.close()
        
        bms = json.loads(json_object[str(msid)])
        
        print(bms)
        
        # await ctx.message.reply(f"Beatmap {bms["title"]} of ID {bms["id"]} has been loaded into the database.")
    else:
        # await ctx.message.reply(f"Beatmap {bms["title"]} of ID {bms["id"]} has already been loaded.")
        return
    

client.run(os.getenv("token"))