from loadmaps import find_ubmo, return_json, save_to_json, User_To_Dict, BeatmapDiff_To_Dict
from jsontools import Dict_To_UBMO, UBMO_To_Dict
import random

# User class for...users obviously why do you even need this comment
class User:
    def __init__(self, id, maps=[], items={}, pp=0, rolls_amount=25, rank=0, roll_max=25):
        self.id = id
        self.maps = maps
        self.items = items
        self.pp = pp
        self.rolls_amount = rolls_amount
        self.rank = rank
        self.roll_max = roll_max
    
    async def add_map(self, map):
        for i in self.maps:
            if i.id == map.parent_id:        
                await i.add_difficulty(map)
                
                return
          
        ubmo = await find_ubmo(map.parent_id)
        
        await ubmo.add_difficulty(map)
        
        self.maps.append(ubmo)
    
    async def add_mapper(self, mapper):
        self.mappers.append(mapper)
    
    async def add_item(self, item, type):
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
    
    result = User(data["id"], maps, data["items"], data["pp"], data["rolls_amount"], data["rank"], data["roll_max"])
    
    return result

# Calculate which shards to give player based on probabilities
# Algorithm in dev-notes
# 1 - common shard
# 2 - uncommon shard
# 3 - rare shard
# 4 - epic shard
# 5 - mythic shard
# 6 - legendary shard
# 7 - chromatic shard
# 8 - ultra shard
SR_TABLE = {
    (0, 1): {
        "guaranteed": 1,
        "rolls": []
    },
    (1, 2): {
        "guaranteed": 1,
        "rolls": [(1, 0.80), (2, 0.20)]
    },
    (2, 3): {
        "guaranteed": 1,
        "rolls": [(1, 0.60), (2, 0.30), (3, 0.10)]
    },
    (3, 4): {
        "guaranteed": 2,
        "rolls": [(1, 0.40), (2, 0.40), (3, 0.20)]
    },
    (4, 5): {
        "guaranteed": 2,
        "rolls": [(1, 0.10), (2, 0.60), (3, 0.25), (4, 0.05)]
    },
    (5, 6): {
        "guaranteed": 3,
        "rolls": [(2, 0.40), (3, 0.45), (4, 0.15)]
    },
    (6, 7): {
        "guaranteed": 3,
        "rolls": [(2, 0.10), (3, 0.60), (4, 0.30)]
    },
    (7, 8): {
        "guaranteed": 4,
        "rolls": [(3, 0.30), (4, 0.50), (5, 0.20)]
    },
    (8, 9): {
        "guaranteed": None,  # epic/mythic 50/50
        "rolls": [(3, 0.10), (4, 0.40), (5, 0.40), (6, 0.10)]
    },
    (9, 10): {
        "guaranteed": 5,
        "rolls": [(5, 0.40), (6, 0.40), (7, 0.20)]
    },
    (10, 11): {
        "guaranteed": 6,
        "rolls": [(6, 0.40), (7, 0.60)]
    },
    (11, 12): {
        "guaranteed": 7,
        "rolls": [(6, 0.10), (7, 0.70), (8, 0.20)]
    },
    (12, 14): {
        "guaranteed": None,  # chromatic/ultra 50/50
        "rolls": [(7, 0.50), (8, 0.50)]
    }
}

def get_shards(sr: float) -> list[int]:
    sr = min(sr, 14)

    shards = []

    for (low, high), data in SR_TABLE.items():
        if low <= sr < high:

            if data["guaranteed"] is None:
                if (low, high) == (8, 9):
                    shards.append(random.choice([4, 5])) 
                elif (low, high) == (12, 14):
                    shards.append(random.choice([7, 8]))  
            else:
                shards.append(data["guaranteed"])

            for shard_id, chance in data["rolls"]:
                if random.random() < chance:
                    shards.append(shard_id)

            return shards

    raise ValueError("SR out of supported range")


async def give_rewards(user, maps):
    pass

# UserPool object that stores all users in User object form and json form
class UserPool:
    def __init__(self, users={}, users_json={}):
        self.users = users
        self.users_json = users_json
        
    async def load_from(self, file):
        self.users_json = await return_json(file)
        
        for i in self.users_json:
            self.users[i] = await Dict_To_User(self.users_json[i])
            
    async def update_user(self, id, new):
        self.users[str(id)] = new
        self.users_json[str(id)] = await User_To_Dict(new)
        
    async def clear_all(self):
        self.users = {}
        self.users_json = {}
            
    async def save_to(self, file):
        await save_to_json(file, self.users_json)