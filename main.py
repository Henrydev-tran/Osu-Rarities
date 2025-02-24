import os
import random
import copy
import json

import asyncio

import discord
from discord.ext import commands

from dotenv import load_dotenv

load_dotenv()

from raritycalculation import Calculate_Rarity
from jsontools import Beatmap_To_Json
from loadmaps import *
from probabilitycalc import *

client = commands.Bot(command_prefix='o!', intents=discord.Intents(messages=True, guilds=True, message_content=True))
client.remove_command("help")

@client.command('ping')
async def ping(ctx):
    await ctx.message.reply("hi")

@client.command("calculaterarity")
async def calcrare(ctx, sr):
    await ctx.message.reply(f"The given star rating of {sr} has a rarity of 1 in {round(Calculate_Rarity(sr))}")
    
@client.command("load_beatmapset")
async def loadbms(ctx, bms):
    await ctx.message.reply(await load_beatmapset(bms))
    
@client.command("loadbms_intodatabase")
async def loadbmsintodatabase(ctx, msid):
    if ctx.author.id == 718102801242259466:
        bms = None
        
        json_object = None
        
        file = open("json/maps.json", "r")
        json_object = json.load(file)
        file.close()
        
        try:
            bms = json_object[str(msid)]
        except:
            json_object[str(msid)] = await load_beatmapset(msid)
            file = open("json/maps.json", "w")
            json.dump(json_object, file)
            file.close()
            
            bms = json_object[str(msid)]
            
            
            await ctx.message.reply(f"Beatmap {bms["title"]} of ID {bms["id"]} has been loaded into the database.")
        else:
            bms = json_object[str(msid)]
            
            await ctx.message.reply(f"Beatmap {bms["title"]} of ID {bms["id"]} has already been loaded.")
            return
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    

async def loadbms(msid):
    bms = None
    
    json_object = None
    
    file = open("json/maps.json", "r")
    json_object = json.load(file)
    file.close()
    
    try:
        bms = json_object[str(msid)]
    except:
        try:
            json_object[str(msid)] = await load_beatmapset(msid)
        except:
            return 1
        file = open("json/maps.json", "w")
        json.dump(json_object, file)
        file.close()
    else:
        return 1
    
    return 0

@client.command("load_next")
async def loadnext_page(ctx):
    if ctx.author.id == 718102801242259466:
        await loadnpage()
        
        await ctx.message.reply("Loaded 50 new beatmaps into the database")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
@client.command("load_multipages")
async def loadmanypages(ctx, num):
    if ctx.author.id == 718102801242259466:
        amount_maps = 0
        
        for i in range(int(num)):
            await loadnpage()
            amount_maps += 50
        
        await ctx.message.reply(f"{amount_maps} maps has been loaded!")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
@client.command("mapsloaded")
async def loadedamount(ctx):
    file = open("json/maps.json", "r")
    json_object = json.load(file)
    file.close()
    
    await ctx.message.reply(f"This bot has loaded {len(json_object)} maps into its database.")
    
@client.command("load_diffs_sorted")
async def load_nmz_diffs(ctx):
    if ctx.author.id == 718102801242259466:
        await add_diffs_to_sorted_file()
        
        await ctx.message.reply("Done.")
        
        return  
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
@client.command("calculate_ranges")
async def load_nmz_diffs(ctx):
    if ctx.author.id == 718102801242259466:
        await add_ranges_to_file()
        
        await ctx.message.reply("Done.")
        
        return  
    
    await ctx.message.reply("You do not have the permission to use this command.") 
    
@client.command("load_normalized_diffs")
async def load_nmz_diffs(ctx):
    if ctx.author.id == 718102801242259466:
        await add_normalized_diffs_to_sorted_file()
        
        await ctx.message.reply("Done.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
    
@client.command("roll")
async def roll_random(ctx):
    result = await get_random_map()
    
    await ctx.message.reply(f"Rolled {result["title"]}[{result["difficulty_name"]}] with Star Rating of {result["star_rating"]} and Rarity of 1 in {result["rarity"]}")

@client.command("clear_all_maps")
async def clear_maps_cmd(ctx):
    if ctx.author.id == 718102801242259466:
        file = open("json/maps.json", "r")
        json_object = json.load(file)
        file.close()
        
        await ctx.message.reply(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {len(json_object)} maps gets cleared")
        print(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {len(json_object)} maps gets cleared")
        
        await asyncio.sleep(20)
        
        file = open("json/maps.json", "w")
        file.write("{}")
        file.close()
        
        file = open("json/bmpage.count", "w")
        file.write("0")
        file.close()
        
        await ctx.message.reply("All maps have been cleared.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
        

@client.command("clear_sorted_diffs")
async def clear_sorted_diffs_cmd(ctx):
    if ctx.author.id == 718102801242259466:
        file = open("json/sorteddiffs.json", "r")
        json_object = json.load(file)
        file.close()
        
        await ctx.message.reply(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {len(json_object)} difficulties gets cleared")
        print(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {len(json_object)} difficulties gets cleared")
        
        await asyncio.sleep(20)
        
        file = open("json/sorteddiffs.json", "w")
        file.write("[]")
        file.close()
        
        await ctx.message.reply("All difficulties have been cleared.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
    
@client.command("help")
async def help(ctx):
    await ctx.message.reply("Check DMs.")
    
    await ctx.author.send("""Prefix - o!
ping - Check status of Bot. example: o!ping.
calculaterarity - Calculate rarity of a given star rating. Arguments: <sr>. example: o!calculaterarity 7.86.
load_beatmapset - Returns json data of a beatmapset with a given bms id. Arguments: <bms_id>. example: o!load_beatmapset 2288709.
mapsloaded - Check how many maps has been loaded into the database. example: o!mapsloaded.
help - Shows this message.
7 more dev-only commands.""")
    
@client.command("recalculate_rarities")
async def recalculate_rarities(ctx):
    if ctx.author.id == 718102801242259466:
        file = open("json/maps.json", "r")
        json_object = json.load(file)
        file.close()
        
        for i in json_object:
            for y in json_object[i]["difficulties"]:
                y["rarity"] = Calculate_Rarity(y["star_rating"])
                
        file = open("json/maps.json", "w")
        json.dump(json_object, file)
        file.close()
                
        await ctx.message.reply("Done.")
        
        return
        
    await ctx.message.reply("You do not have the permission to use this command.")

client.run(os.getenv("token"))