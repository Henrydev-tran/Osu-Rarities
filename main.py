import os
import random
import copy
import json

import discord
from discord.ext import commands

from ossapi.enums import RankStatus

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
        bms = json_object[str(msid)]
        print(bms)
    except:
        json_object[str(msid)] = load_beatmapset(msid)
        file = open("maps.json", "w")
        json.dump(json_object, file)
        file.close()
        
        bms = json.loads(json_object[str(msid)])
        
        
        await ctx.message.reply(f"Beatmap {bms["title"]} of ID {bms["id"]} has been loaded into the database.")
    else:
        bms = json.loads(json_object[str(msid)])
        
        await ctx.message.reply(f"Beatmap {bms["title"]} of ID {bms["id"]} has already been loaded.")
        return
    

def loadbms(msid):
    bms = None
    
    json_object = None
    
    file = open("maps.json", "r")
    json_object = json.load(file)
    file.close()
    
    try:
        bms = json_object[str(msid)]
    except:
        try:
            json_object[str(msid)] = load_beatmapset(msid)
        except:
            return 1
        file = open("maps.json", "w")
        json.dump(json_object, file)
        file.close()
    else:
        return 1
    
    return 0

def add_blacklist(id):
    file = open("beatmapblacklist.json", "r")
    json_object = json.load(file)
    file.close()
    
    json_object.append(id)
    print(len(json_object))
    
    file = open("beatmapblacklist.json", "w")
    json.dump(json_object, file)
    file.close()
    
def check_blacklist(id):
    file = open("beatmapblacklist.json", "r")
    json_object = json.load(file)
    file.close()
    
    return id in json_object

def load_randombms():
    # I have no idea what this code is
    
    id = random.randint(1, 2200000)
    
    while check_blacklist(id):
        id = random.randint(1, 2200000)
        
    result = None
    
    while True:
        try:
            while check_blacklist(id):
                id = random.randint(1, 2200000)
            
            result = load_beatmapset(id)
            break
        except:
            add_blacklist(id)
            id = random.randint(1, 2200000)
    
    while json.loads(result)["status"] != 4 and json.loads(result)["status"] != 1:
        add_blacklist(id)
        id = random.randint(1, 2200000)
        while True:
            try:
                while check_blacklist(id):
                    id = random.randint(1, 2200000)
                
                result = load_beatmapset(id)
                break
            except:
                add_blacklist(id)
                id = random.randint(1, 2200000)
    
    loadbms(id)
    
    print(f"Mapset with ID: {id} loaded")
        
@client.command("bulkload_random")
async def bulkloadrand(ctx, amount):
    for i in range(int(amount)):
        load_randombms()

client.run(os.getenv("token"))