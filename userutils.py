from loadmaps import find_ubmo, return_json, save_to_json, User_To_Dict, BeatmapDiff_To_Dict
from jsontools import Dict_To_UBMO, UBMO_To_Dict, Dict_To_Item
import random
from raritycalculation import calculatepp
import math, asyncio
from collections import Counter
from item import SHARDS, STARESSENCE
import copy
import time

# User class for...users obviously why do you even need this comment
class User:
    DEFAULTS = {
        "pp": 0,
        "rolls_amount": 25,
        "rank": 0,
        "roll_max": 25,
        "luck_mult": 1,
        "xp": 0,
        "level": 1,
        "dev_luck_base": 1,
        "roll_cooldown": 1.0,
        "roll_window_seconds": 300,
        "roll_timestamps": [],
        "display_name": None,
        "is_fake": False,
        "equipped_map_id": None,
        "rarest_rolled_rarity": 0,
    }

    def __init__(self, id, maps=[], items={}, **kwargs):
        self.id = id
        self.maps = maps
        self.items = items
        
        # Set default values
        for key, default in self.DEFAULTS.items():
            value = kwargs.get(key, default)
            if key == "roll_timestamps" and value is None:
                value = []
            setattr(self, key, value)
        
        # Set any extra fields from kwargs
        for k, v in kwargs.items():
            if k not in self.DEFAULTS and not hasattr(self, k):
                setattr(self, k, v)
    
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
                
        if type in ("Special"):
            specialitem = self.items.setdefault(type, {})
            
            try:
                specialitem[item.id].duplicates += item.duplicates
            except:    
                specialitem[item.id] = item
                
        if type == "Tool":
            tools = self.items.setdefault("Tool", {})
            
            try:
                tools[item.id].duplicates += item.duplicates
            except:    
                tools[item.id] = item
                
        if type == "Gear" or type == "GearPeripheral":
            gear = self.items.setdefault(type, {})
            # enforce one-per-type cap for Gears and Gear Peripherals by treating duplicates as at most 1
            existing = gear.get(item.id)
            if existing:
                # already have this Gear type; cap at 1 (no stacking)
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

        The calculation starts from the developer luck base and applies each gear item 'duplicates' times.
        The resulting value is stored in `self.luck_mult` and returned.
        """
        base_luck = float(getattr(self, "dev_luck_base", 1.0))
        playerluck = base_luck

        gear_items = self.items.get("Gear", {})
        
        peripheralitems = self.items.get("GearPeripheral", {})
        equipped_peripherals = [item for item in peripheralitems.values() if getattr(item, 'equipped', False)]
        gear_items.update({item.id: item for item in equipped_peripherals})
        
        for gear in gear_items.values():
            # treat duplicates as at most 1 to enforce one-per-type behavior
            times = min(1, max(0, int(getattr(gear, 'duplicates', 0))))
            for _ in range(times):
                playerluck = playerluck * getattr(gear, 'luckmultiplier', 1) + getattr(gear, 'luckincrease', 0)

        # store as the user's luck multiplier
        self.luck_mult = round(playerluck)
        return self.luck_mult
                
    def get_equipped_map(self):
        equipped_id = getattr(self, 'equipped_map_id', None)
        if equipped_id is None:
            return None

        for ubmo in self.maps:
            for diff in getattr(ubmo, 'difficulties', []):
                if diff.id == equipped_id:
                    return diff

        return None

    def remove_item_by_id(self, id, amount):
        obj = self.find_item_by_id(id)
        if obj is not None:
            obj.duplicates -= amount

    def get_eligible_map_lookup(self, min_star=None, max_star=None, include_min=True, include_max=True):
        """Return a lookup of map difficulty id -> owned User_BMD_Object for matching star filters."""
        result = {}

        for ubmo in self.maps:
            for diff in ubmo.difficulties:
                sr = getattr(diff, "sr", None)
                if sr is None:
                    continue

                if min_star is not None:
                    if include_min:
                        if sr < min_star:
                            continue
                    else:
                        if sr <= min_star:
                            continue

                if max_star is not None:
                    if include_max:
                        if sr > max_star:
                            continue
                    else:
                        if sr >= max_star:
                            continue

                result[diff.id] = diff

        return result

    def count_eligible_maps(self, min_star=None, max_star=None, include_min=True, include_max=True):
        lookup = self.get_eligible_map_lookup(
            min_star=min_star,
            max_star=max_star,
            include_min=include_min,
            include_max=include_max,
        )
        return sum(getattr(diff, "duplicates", 0) for diff in lookup.values())

    def remove_maps_by_id_list(self, diff_ids):
        """Consume owned map difficulties by id. Repeated ids consume duplicates."""
        counts = Counter(diff_ids)

        # Validate ownership before mutating state
        owned_lookup = self.get_eligible_map_lookup()
        for diff_id, amount in counts.items():
            owned_diff = owned_lookup.get(diff_id)
            owned_amount = getattr(owned_diff, "duplicates", 0) if owned_diff is not None else 0
            if owned_amount < amount:
                raise ValueError(f"Not enough copies of map id {diff_id} to consume.")

        for ubmo in self.maps:
            remaining_difficulties = []
            for diff in ubmo.difficulties:
                to_remove = counts.get(diff.id, 0)
                if to_remove <= 0:
                    remaining_difficulties.append(diff)
                    continue

                diff.duplicates -= to_remove
                counts[diff.id] = 0

                if diff.duplicates > 0:
                    remaining_difficulties.append(diff)

            ubmo.difficulties = remaining_difficulties

        self.maps = [ubmo for ubmo in self.maps if ubmo.difficulties]

        if getattr(self, 'equipped_map_id', None) is not None and self.get_equipped_map() is None:
            self.equipped_map_id = None
        
    def add_item_by_id(self, id, amount):
        obj = self.find_item_by_id(id)
        if obj is not None:
            obj.duplicates += amount
    
    def count_item_by_id(self, id):
        # Search all item categories and return the duplicates for the matching item id
        for items in self.items.values():
            found = next((obj for obj in items.values() if obj.id == id), None)
            if found is not None:
                print(f"Found item with id {id}, duplicates: {getattr(found, 'duplicates', 0)}")
                
                # If the item type is a Tool, always return 1 since Tools are one-per-type
                if getattr(found, 'type', None) == 'Tool':
                    return 1
                
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

    def _prune_roll_timestamps(self, now=None):
        if now is None:
            now = time.time()

        cutoff = now - self.roll_window_seconds
        self.roll_timestamps = [ts for ts in self.roll_timestamps if ts > cutoff]

    async def can_roll(self):
        now = time.time()
        self._prune_roll_timestamps(now)

        if self.roll_timestamps:
            next_allowed = self.roll_timestamps[-1] + self.roll_cooldown
            if now < next_allowed:
                return False, max(0.0, next_allowed - now), "cooldown"

        if len(self.roll_timestamps) >= self.roll_max:
            retry_after = self.roll_timestamps[0] + self.roll_window_seconds - now
            return False, max(0.0, retry_after), "roll_limit"

        return True, 0.0, None

    async def register_roll(self):
        now = time.time()
        self._prune_roll_timestamps(now)
        self.roll_timestamps.append(now)

    async def set_roll_max(self, new_roll_max):
        self.roll_max = max(1, int(new_roll_max))

    async def set_roll_cooldown(self, new_cooldown_seconds):
        # Keep a small lower bound to avoid zero/negative spam loops.
        self.roll_cooldown = max(0.05, float(new_cooldown_seconds))
    
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

# Returns the xp required to reach the next level
# Params: level, base xp for l1, growth of xp/level
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
        
    
    dev_luck_base = data.get("dev_luck_base", data.get("luck_mult", 1))
    kwargs = {k: v for k, v in data.items() if k not in ["id", "maps", "items"]}
    kwargs["dev_luck_base"] = dev_luck_base  # Ensure it's set
    result = User(data["id"], maps, items, **kwargs)
    
    return result

# List of all shards
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

# Returns the chance of getting a Star Essence from a given star rating
def star_essence_chance(sr):
    return min(100, 5 * 20 ** ((sr - 1) / 6)) / 100

# Returns star essence rewards based on given maps
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
                
# Stores the rewards for selling maps
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

# Gets the SR_TABLE entry for a given star rating, handling the special case of >14 as ultra
def _get_sr_entry(sr: float):
    if sr > 14:
        return None  # special ultra handling
    key = int(math.floor(sr))
    return _SR_LOOKUP.get(key)

# Return shard ids for a single roll (one duplicate). Optimized lookup.
def get_shards_single(sr: float) -> list[int]:
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

# Return a Counter mapping shard_id -> count for `duplicates` independent rolls.
def get_shards_aggregate(sr: float, duplicates: int) -> Counter:
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

# Returns rewards obtained from given maps
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