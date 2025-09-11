from loadmaps import find_beatmap
from jsontools import Dict_To_UBMO

# User class for...users obviously why do you even need this comment
class User:
    def __init__(self, id, maps=[], mappers=[], items=[], pp=0, rolls_amount=0, rank=0):
        self.id = id
        self.maps = maps
        self.mappers = mappers
        self.items = items
        self.pp = pp
        self.rolls_amount = rolls_amount
        self.rank = rank
    
    async def add_map(self, map):
        for i in self.maps:
            if i.id == map.parent_id:
                await i.add_difficulty(map)
                
        ubmo = await find_beatmap(map.parent_id)
        await ubmo.add_difficulty(map)
        
        self.maps.append(ubmo)
    
    async def add_mapper(self, mapper):
        self.mappers.append(mapper)
    
    async def add_item(self, item):
        self.items.append(item)
    
    async def change_pp(self, amount):
        self.pp += amount
    
    async def add_rolls(self, amount):
        self.rolls_amount += amount
    
    async def change_rank(self, new_rank):
        self.rank = new_rank
        
# Returns a User object from a given Dict
async def Dict_To_User(data):
    maps = []
    
    for i in data["maps"]:
        maps.append(await Dict_To_UBMO(i))
    
    result = User(data["id"], maps, data["mappers"], data["items"], data["pp"], data["rolls_amount"], data["rank"])
    
    return result