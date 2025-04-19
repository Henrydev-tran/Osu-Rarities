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

rolling_disabled = False

# Check if bot is online/working properly
@client.command('ping')
async def ping(ctx):
    await ctx.message.reply("hi")

# Calculate the rarity of a given star rating
@client.command("calculaterarity")
async def calcrare(ctx, sr):
    await ctx.message.reply(f"The given star rating of {sr} has a rarity of 1 in {round(Calculate_Rarity(sr))}")

# Load the beatmapset of a given ID and outputs it
@client.command("load_beatmapset")
async def loadbms(ctx, bms):
    await ctx.message.reply(await load_beatmapset(bms))

# Load a beatmapset of a given ID and saves it into database (dev only)
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
    
# Basically the function above without the discord context
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

# Load the next page of beatmapsets (dev only)
@client.command("load_next")
async def loadnext_page(ctx):
    if ctx.author.id == 718102801242259466:
        await loadnpage()
        
        await ctx.message.reply("Loaded 50 new beatmaps into the database")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
# Load the next given amount of pages (dev only)
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
    
# Check the amount of maps loaded in the database
@client.command("mapsloaded")
async def loadedamount(ctx):
    file = open("json/maps.json", "r")
    json_object = json.load(file)
    file.close()
    
    await ctx.message.reply(f"This bot has loaded {len(json_object)} maps into its database.")

# Reset the internal page count (dev only)
@client.command("reset_page_count")
async def reset_page_count(ctx):
    if ctx.author.id == 718102801242259466:
        await reset_page_count()
        await ctx.message.reply("Done.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 
    
# Turn rolling on/off for all users (dev only)
@client.command("toggle_rolling")
async def disable_rolling(ctx):
    global rolling_disabled
    
    if ctx.author.id == 718102801242259466:
        if rolling_disabled:
            rolling_disabled = False
            await ctx.message.reply("Rolling Enabled.")
        if not rolling_disabled:
            rolling_disabled = True
            await ctx.message.reply("Rolling disabled.")
            
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 
        
# Add all difficulties to sorted file for sorting (dev only)
@client.command("load_diffs_sorted")
async def load_nmz_diffs(ctx):
    if ctx.author.id == 718102801242259466:
        await add_diffs_to_sorted_file()
        
        await ctx.message.reply("Done.")
        
        return  
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
# Calculate the ranges of rarities for sorted beatmaps (dev only)
@client.command("calculate_ranges")
async def load_nmz_diffs(ctx):
    if ctx.author.id == 718102801242259466:
        await add_ranges_to_file()
        
        await ctx.message.reply("Done.")
        
        return  
    
    await ctx.message.reply("You do not have the permission to use this command.") 

# Normalize all ranges in file (dev only)
@client.command("load_normalized_diffs")
async def load_nmz_diffs(ctx):
    if ctx.author.id == 718102801242259466:
        await add_normalized_diffs_to_sorted_file()
        
        await ctx.message.reply("Done.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
    
# Roll a beatmap
@client.command("roll")
async def roll_random(ctx):
    if not rolling_disabled:
        result = await get_random_map()
        
        await ctx.message.reply(f"Rolled {result["title"]}[{result["difficulty_name"]}] with Star Rating of {result["star_rating"]} and Rarity of 1 in {result["rarity"]}")
        
        return
        
    await ctx.message.reply("Rolling had been temporarily disabled by the developer.")

# Clear ALL maps in the database (dev only, risky)
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
        
# Clear ALL sorted maps in the database (dev only, risky)
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
    
# Check available commands
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

# Test the embed function (temporary, to be removed soon)
@client.command("test_embed")
async def test_embed(ctx):
    embed = discord.Embed(title="You rolled Parallel Universe Shifter[Quantum Field Disruption]! (1 in 126900)", description="Star Rating: 8.54 ⭐", color=0x0362fc)
    embed.add_field(name="Field1", value="test embed", inline=False)
    embed.add_field(name="Field2", value="Open the gates to the parallel universes.", inline=False)
    embed.add_field(name="lmao", value="test embed", inline=False)
    embed.set_image(url="https://assets.ppy.sh/beatmaps/2062263/covers/cover.jpg")
    embed.set_footer(text="Time: hh:mm dd/mm/yyyy")
    embed.set_thumbnail(url="https://b.ppy.sh/thumb/2062263l.jpg")
    
    await ctx.message.reply(embed=embed)

client.run(os.getenv("token"))