import os

import asyncio

import discord
from discord.ext import commands

from user_handling import *

from dotenv import load_dotenv

load_dotenv()

from raritycalculation import Calculate_Rarity, get_star_color
from jsontools import Beatmap_To_Json
from loadmaps import *
from probabilitycalc import *
from math import ceil

import datetime

client = commands.Bot(command_prefix='o!', intents=discord.Intents(messages=True, guilds=True, message_content=True))
client.remove_command("help")



########################## UTILS ##########################

# Maps the star rating into color emojis
emoji_map = {
    1: "<:1_:1415986345670606949>",
    2: "<:2_:1415986479062057020>",
    3: "<:3_:1415986584498606130>",
    4: "<:4_:1415986680267014144>",
    5: "<:5_:1415986831907885147>",
    6: "<:6_:1415986916394012806>",
    7: "<:7_:1415987059868434462>", 
    8: "<:8_:1415987148124979240>", 
    9: "<:9_:1415987239909064816>", 
    10: "<:10:1415987332552720426>", 
    11: "<:11:1415987398994558996>", 
    12: "<:12:1415987514371473488>", 
    13: "<:13:1415987587029667931>", 
    14: "<:14:1415987664330424320>", 
    15: "<:15:1415987720001552416>"
}

# Returns an emoji id from a given star rating
def get_star_emoji(star_rating: float) -> str:
    star = round(star_rating)
    if star < 1: star = 1
    if star > 15: star = 15
    return emoji_map.get(star, "<:15:345678901234567890>")

# Split a list into chunks of given size
def chunk_list(lst, size):
    return [lst[i:i + size] for i in range(0, len(lst), size)]

# Class displays maps in a paging system
class MapPaginator(discord.ui.View):
    def __init__(self, maps, username, per_page=10):
        super().__init__(timeout=120)
        self.pages = chunk_list(maps, per_page)
        self.index = 0
        self.username = username

    def make_embed(self):
        embed = discord.Embed(
            title=f"{self.username}'s Maps",
            color=discord.Color.blurple()
        )

        for m in self.pages[self.index]:
            difficulties = "\n".join(
                f"{get_star_emoji(d['star_rating'])} "
                f"- {d['difficulty_name']} ⭐ {d['star_rating']} (rarity {d['rarity']})"
                for d in m["difficulties"]
            )

            embed.add_field(
                name=f"{m['title']} — {m['artist']} (by {m['mapper']})",
                value=difficulties,
                inline=False
            )

        embed.set_footer(text=f"Page {self.index+1}/{len(self.pages)}")
        return embed

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pages) - 1:
            self.index += 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)

            
###########################################################

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
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        bms = None
        
        json_object = await return_json("json/maps.json")
        
        try:
            bms = json_object[str(msid)]
        except:
            json_object[str(msid)] = await load_beatmapset(msid)
            await save_to_json("json/maps.json", json_object)
            
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
    
    json_object = await return_json("json/maps.json")
    
    try:
        bms = json_object[str(msid)]
    except:
        try:
            json_object[str(msid)] = await load_beatmapset(msid)
        except:
            return 1
        await save_to_json("json/maps.json", json_object)
    else:
        return 1
    
    return 0

# Load the next page of beatmapsets (dev only)
@client.command("load_next")
async def loadnext_page(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await loadnpage()
        
        await ctx.message.reply("Loaded 50 new beatmaps into the database")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
# Load the next given amount of pages (dev only)
@client.command("load_multipages")
async def loadmanypages(ctx, num):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
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
    json_object = await return_json("json/maps.json")
    
    await ctx.message.reply(f"This bot has loaded {len(json_object)} maps into its database.")

# Reset the internal page count (dev only)
@client.command("reset_page_count")
async def rpc(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await reset_page_count()
        await ctx.message.reply("Done.")
        print("Reseted page back to 0.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 
    
# set the internal page count (dev only)
@client.command("spc")
async def spc(ctx, page):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await set_page_count(page)
        await ctx.message.reply("Done.")
        print(f"Set page to {page}.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 
    
# Change query of bot search
@client.command("change_year")
async def bot_change_year(ctx, year):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await change_year(year)
        await set_query_year(await get_year())
        await ctx.message.reply(f"Done, changed the query date to {str(year)}")
        print(f"Done, changed the query date to {str(year)}")
        
        return
        
    await ctx.message.reply("You do not have the permission to use this command.") 
    
# Turn rolling on/off for all users (dev only)
@client.command("toggle_rolling")
async def disable_rolling(ctx):
    global rolling_disabled
    
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        if rolling_disabled:
            rolling_disabled = False
            await ctx.message.reply("Rolling Enabled.")
        if not rolling_disabled:
            rolling_disabled = True
            await ctx.message.reply("Rolling disabled.")
            
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 
        
# Add all difficulties to sorted file for sorting (dev only). Step 1
@client.command("load_diffs_sorted")
async def load_nmz_diffs(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await add_diffs_to_sorted_file()
        
        await ctx.message.reply("Done.")
        
        return  
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
# Acumulate all ranges in file (dev only). Step 2
@client.command("load_cumulative_diffs")
async def load_nmz_diffs(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await add_cumulative_diffs_to_sorted_file()
        
        await ctx.message.reply("Done.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
    
# Calculate the ranges of rarities for sorted beatmaps (dev only). Step 3
@client.command("calculate_ranges")
async def load_nmz_diffs(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await add_ranges_to_file()
        
        await ctx.message.reply("Done.")
        
        return  
    
    await ctx.message.reply("You do not have the permission to use this command.") 
    
# Roll a beatmap
@client.command("roll")
async def roll_random(ctx):
    if not rolling_disabled:
        userdata = await login(ctx.author.id)
        
        result = await get_random_map()
        
        embed = discord.Embed(title=f"You rolled {result["title"]}[{result["difficulty_name"]}]! (1 in {result["rarity"]})", description=f"Star Rating: {result["star_rating"]} ⭐", color=await get_star_color(result["star_rating"]), timestamp=datetime.datetime.now())
        embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{result["id"]}/covers/cover.jpg")
        embed.set_thumbnail(url=f"https://b.ppy.sh/thumb/{result["id"]}l.jpg")
        
        map_result = await Dict_to_BeatmapDiff(result)
        
        parent = await find_beatmap(map_result.parent_id)
        
        embed.add_field(name="Artist", value=parent.artist)
        embed.add_field(name="Mapper", value=parent.mapper)
        embed.add_field(name="BeatmapsetID", value=parent.id)
        embed.add_field(name="BeatmapID", value=result["id"])
        embed.add_field(name="Status", value=await get_status(parent.status))
        
        await userdata.add_map(map_result)
        
        await update_user(userdata)
        
        await ctx.message.reply(embed=embed)
        
        return
        
    await ctx.message.reply("Rolling had been temporarily disabled by the developer.")
    
@client.command("clear_userdata")
async def clear_userdata_cmd(ctx, id):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:    
        await clear_userdata(id)
        
        await ctx.message.reply("Done.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
    
# Clear ALL userdata in the database (dev only, risky)
@client.command("clear_all_userdata")
async def clear_all_userdata_cmd(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        json_object = await return_json("json/users.json")
        
        await ctx.message.reply(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {len(json_object)} users gets cleared")
        print(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {len(json_object)} users gets cleared")
        
        await asyncio.sleep(20)
        
        await clear_userdata_all()
        
        await ctx.message.reply("All users have been cleared.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")

# Clear ALL maps in the database (dev only, risky)
@client.command("clear_all_maps")
async def clear_maps_cmd(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        json_object = await return_json("json/maps.json")
        
        await ctx.message.reply(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {len(json_object)} maps gets cleared")
        print(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {len(json_object)} maps gets cleared")
        
        await asyncio.sleep(20)
        
        async with aiofiles.open("json/maps.json", "w") as file:
            await file.write("{}")
        
        async with aiofiles.open("json/bmpage.count", "w") as file:
            await file.write("0")
        
        await ctx.message.reply("All maps have been cleared.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
        
# Clear ALL sorted and ranges maps in the database (dev only, risky)
@client.command("clear_sorted_diffs")
async def clear_sorted_diffs_cmd(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        json_object = await return_json("json/sorteddiffs.json")
        
        await ctx.message.reply(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {len(json_object)} difficulties gets cleared")
        print(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {len(json_object)} difficulties gets cleared")
        
        await asyncio.sleep(20)
        
        async with aiofiles.open("json/sorteddiffs.json", "w") as file:
            await file.write("[]")
        
        async with aiofiles.open("json/ranges.json", "w") as file:
            await file.write("[]")
        
        await ctx.message.reply("All difficulties have been cleared.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
    
# Update optimization variables in case range or maps file change (dev only)
@client.command("uov")
async def uov(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await update_optimization_variables()
        await load_gmaps_variable()
        await write_stored_variable()
        await ctx.message.reply("Done.")
        
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
    
@client.command("inventory")
async def inventory(ctx, id = None):
    userdata = None
    username = None
    
    if id == None:
        userdata = await login(ctx.author.id)
        username = ctx.author.display_name
    else:
        userdata = await login(id)
        user = await client.fetch_user(id)
        username = user.name
        
    
    user_json = await User_To_Dict(userdata)
    
    maps = user_json["maps"]
    
    view = MapPaginator(maps, username, per_page=10)
    await ctx.send(embed=view.make_embed(), view=view)
    
    
@client.command("recalculate_rarities")
async def recalculate_rarities(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        json_object = await return_json("json/maps.json")
        
        for i in json_object:
            for y in json_object[i]["difficulties"]:
                y["rarity"] = Calculate_Rarity(y["star_rating"])
                
        await save_to_json("json/maps.json", json_object)
                
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