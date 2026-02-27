from loadmaps import find_ubmo, return_json, save_to_json, User_To_Dict, BeatmapDiff_To_Dict
from jsontools import Dict_To_UBMO, UBMO_To_Dict, Dict_To_Item
import random
from raritycalculation import calculatepp
import math
from collections import Counter
from item import SHARDS, STARESSENCE
import copy

# User class for...users obviously why do you even need this comment
class User:
    def __init__(self, id, maps=[], items={}, pp=0, rolls_amount=25, rank=0, roll_max=25, luck_mult=1, xp=0, level=1):
        self.id = id
        self.maps = maps
        self.items = items
        self.pp = pp
        self.rolls_amount = rolls_amount
        self.rank = rank
        self.roll_max = roll_max
        self.luck_mult = luck_mult
        self.xp = xp
        self.level = level
    
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
    
    def add_item(self, item, type):
        if type == "Shard":
            shards = self.items.setdefault("Shards", {})
            
            try:
                shards[item.shardrarity].duplicates += item.duplicates
            except:
                shards[item.shardrarity] = item  
                
        if type == "ShardCore":
            shardcores = self.items.setdefault("ShardCores", {})
            
            try:
                shardcores[item.corerarity].duplicates += item.duplicates
            except:
                shardcores[item.corerarity] = item  
                
        if type == "Special":
            specialitem = self.items.setdefault("Special", {})
            
            try:
                specialitem[item.id].duplicates += item.duplicates
            except:    
                specialitem[item.id] = item
                
        if type == "Gear":
            gear = self.items.setdefault("Gear", {})
            # enforce one-per-type cap for Beatmap Charms (Gear)
            existing = gear.get(item.id)
            if existing:
                # already have this charm type; cap at 1 (no stacking)
                existing.duplicates = 1
            else:
                item.duplicates = 1
                gear[item.id] = item
            # recalculate luck when gear is added
            try:
                self.recalculate_luck()
            except Exception:
                pass

    def recalculate_luck(self):
        """Recalculate player's luck multiplier from equipped Gear items.

        Formula applied per gear instance:
            playerluck = playerluck * luckmultiplier + luckincrease

        The calculation starts from base 1.0 and applies each gear item 'duplicates' times.
        The resulting value is stored in `self.luck_mult` and returned.
        """
        base_luck = 1.0
        playerluck = base_luck

        gear_items = self.items.get("Gear", {})
        for gear in gear_items.values():
            # treat duplicates as at most 1 to enforce one-per-type behavior
            times = min(1, max(0, int(getattr(gear, 'duplicates', 0))))
            for _ in range(times):
                playerluck = playerluck * getattr(gear, 'luckmultiplier', 1) + getattr(gear, 'luckincrease', 0)

        # store as the user's luck multiplier
        self.luck_mult = playerluck
        return self.luck_mult
                
    def remove_item_by_id(self, id, amount):
        obj = self.find_item_by_id(id)
        
        obj.duplicates -= amount
        
    def add_item_by_id(self, id, amount):
        obj = self.find_item_by_id(id)
        
        obj.duplicates += amount
    
    def count_item_by_id(self, id):
        # Search all item categories and return the duplicates for the matching item id
        for items in self.items.values():
            found = next((obj for obj in items.values() if obj.id == id), None)
            if found is not None:
                return getattr(found, 'duplicates', 0)

        return 0
    
    def find_item_by_id(self, id):
        # Return the first matching item object by id, searching all categories
        for items in self.items.values():
            found = next((obj for obj in items.values() if obj.id == id), None)
            if found is not None:
                return found

        return None

    async def change_pp(self, amount):
        self.pp += amount
        
    async def edit_pp(self, amount):
        self.pp = amount
    
    async def add_rolls(self, amount):
        self.rolls_amount += amount
    
    async def change_rank(self, new_rank):
        self.rank = new_rank
        
    async def change_luck_mult(self, new_mult):
        self.luck_mult = new_mult
        
    async def add_xp(self, xp):
        self.xp += xp
        leveled_up = False

        while self.xp >= xp_to_next_level(self.level):
            self.xp -= xp_to_next_level(self.level)
            self.level += 1
            leveled_up = True
            
        return leveled_up
        
def xp_to_next_level(level, base=100, growth=1.15):
    return int(base * (growth ** (level - 1)))

# Returns a User object from a given Dict
async def Dict_To_User(data):
    maps = []
    
    for i in data["maps"]:
        maps.append(await Dict_To_UBMO(i))
        
    items = {}
    
    for key1, val1 in data["items"].items():
        for key2, val2 in val1.items():
            items.setdefault(key1, {})
            items[key1][key2] = await Dict_To_Item(val2)   
        
    
    result = User(data["id"], maps, items, data["pp"], data["rolls_amount"], data["rank"], data["roll_max"], data["luck_mult"], data["xp"], data["level"])
    
    return result

SHARD_LIST = [
    "None",
    "Common",
    "Uncommon",
    "Rare",
    "Epic",
    "Mythic",
    "Legendary",
    "Chromatic",
    "Ultra"
]

SHARD_RANK = {rarity: i for i, rarity in enumerate(SHARD_LIST)}

def star_essence_chance(sr):
    return min(100, 5 * 20 ** ((sr - 1) / 6)) / 100

def get_star_essence(maps):
    result = None
    
    for i in maps:
        for _ in range(i.duplicates):
            if random.random() < star_essence_chance(i.sr):
                if result == None:
                    result = copy.deepcopy(STARESSENCE)
                else:
                    result.duplicates += 1
    
    return result
                

class SellRewards:
    def __init__(self, pp, shards, staresc):
        self.pp = pp
        self.baseshards = shards
        self.oldshards = []
        self.shards = {}
        self.staresc = staresc
    
    def convert_shards(self):
        # baseshards can be a Counter mapping shard_id -> count or a list of shard ids
        if isinstance(self.baseshards, Counter):
            for shard_id, count in self.baseshards.items():
                name = SHARD_LIST[shard_id]
                try:
                    self.shards[name].duplicates += count
                except:
                    new_obj = copy.deepcopy(SHARDS[name])
                    new_obj.duplicates = count
                    self.shards[name] = new_obj
        else:
            for i in self.baseshards:
                try:
                    self.shards[SHARD_LIST[i]].duplicates += 1
                except:
                    self.shards[SHARD_LIST[i]] = copy.deepcopy(SHARDS[SHARD_LIST[i]])

        self.baseshards = Counter()
        
    async def get_staresc(self):
        return self.staresc
                
    async def get_shards(self):
        return self.shards
    
    async def get_pp(self):
        return self.pp 

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
        "guaranteed": None,  # epic / mythic 50/50
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
    (12, 13): {
        "guaranteed": None,  # chromatic / ultra 50/50
        "rolls": [(7, 0.50), (8, 0.50)]
    },
    (13, 14): {
        "guaranteed": 8,
        "rolls": [(8, 0.70), (8, 0.50), (7, 0.30)]
    }
}

# Precompute a quick lookup from integer star to SR_TABLE entry to avoid looping SR_TABLE each call
_SR_LOOKUP = {}
for (low, high), data in SR_TABLE.items():
    for i in range(int(low), int(high)):
        _SR_LOOKUP[i] = (low, high, data)

def _get_sr_entry(sr: float):
    if sr > 14:
        return None  # special ultra handling
    key = int(math.floor(sr))
    return _SR_LOOKUP.get(key)

def get_shards_single(sr: float) -> list[int]:
    """Return shard ids for a single roll (one duplicate). Optimized lookup."""
    shards = []

    if sr > 14:
        shards.extend([8] * 5)
        roll = random.random()
        if roll < 0.60:
            shards.extend([8] * 2)
        elif roll < 0.85:
            shards.extend([8] * 4)
        else:
            shards.extend([8] * 6)
        return shards

    entry = _get_sr_entry(sr)
    if entry is None:
        raise ValueError("SR out of supported range")

    low, high, data = entry

    if data["guaranteed"] is None:
        if (low, high) == (8, 9):
            shards.append(random.choice([4, 5]))
        elif (low, high) == (12, 13):
            shards.append(random.choice([7, 8]))
    else:
        shards.append(data["guaranteed"])

    for shard_id, chance in data["rolls"]:
        if random.random() < chance:
            shards.append(shard_id)

    return shards

def get_shards_aggregate(sr: float, duplicates: int) -> Counter:
    """Return a Counter mapping shard_id -> count for `duplicates` independent rolls."""
    counter = Counter()
    if duplicates <= 0:
        return counter

    if sr > 14:
        # each duplicate gives the same base 5 ultras + an extra 2/4/6 based on a roll
        for _ in range(duplicates):
            counter[8] += 5
            roll = random.random()
            if roll < 0.60:
                counter[8] += 2
            elif roll < 0.85:
                counter[8] += 4
            else:
                counter[8] += 6

        return counter

    entry = _get_sr_entry(sr)
    if entry is None:
        raise ValueError("SR out of supported range")

    low, high, data = entry

    # For each duplicate, update counter based on deterministic guaranteed and probabilistic rolls
    for _ in range(duplicates):
        if data["guaranteed"] is None:
            if (low, high) == (8, 9):
                counter[random.choice([4, 5])] += 1
            elif (low, high) == (12, 13):
                counter[random.choice([7, 8])] += 1
        else:
            counter[data["guaranteed"]] += 1

        for shard_id, chance in data["rolls"]:
            if random.random() < chance:
                counter[shard_id] += 1

    return counter

async def give_rewards(maps):
    shard_counts = Counter()
    pp = 0

    for i in maps:
        # aggregate shard rolls for this difficulty using duplicates
        if i.duplicates > 0:
            shard_counts.update(get_shards_aggregate(i.sr, i.duplicates))

        # compute PP once per difficulty and multiply
        sr_for_pp = 15 if i.sr > 15 else i.sr
        pp += calculatepp(sr_for_pp) * i.duplicates

    rewards = SellRewards(pp, shard_counts, get_star_essence(maps))

    rewards.convert_shards()

    return rewards

# UserPool object that stores all users in User object form and json form
class UserPool:
    def __init__(self, users={}, users_json={}):
        self.users = users
        self.users_json = users_json
        
    async def load_from(self, file):
        self.users_json = await return_json(file)
        
        for i in self.users_json:
            self.users[i] = await Dict_To_User(self.users_json[i])
            # ensure luck multiplier reflects any Gear items on startup
            try:
                self.users[i].recalculate_luck()
            except Exception:
                pass
            
    async def update_user(self, id, new):
        self.users[str(id)] = new
        self.users_json[str(id)] = await User_To_Dict(new)
        
    async def clear_all(self):
        self.users = {}
        self.users_json = {}
            
    async def save_to(self, file):
        await save_to_json(file, self.users_json)