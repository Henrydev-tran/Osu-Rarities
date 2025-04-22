from raritycalculation import Calculate_Rarity

# Beatmap object, stores data of a beatmapset
class Beatmap:
    def __init__(self, id, title, artist, difficulties, mapper, status) -> None:
        self.id = id
        self.title = title
        self.artist = artist
        self.difficulties = difficulties
        self.mapper = mapper
        self.status = status
        
# Beatmap_Difficulty object, stores data of a beatmap difficulty
class Beatmap_Difficulty:
    def __init__(self, sr, parent_id, id, title, artist, diff_name) -> None:
        self.id = id
        self.sr = sr
        self.rarity = Calculate_Rarity(self.sr)
        self.parent_id = parent_id
        self.title = title
        self.artist = artist
        self.difficulty_name = diff_name

# Beatmap_Difficulty_Cumulative_Range object, stores data of a beatmap difficulty and its range & cumulative probability
class Beatmap_Difficulty_Cumulative_Range:
    def __init__(self, sr, parent_id, id, title, artist, weight, R, rarity, diff_name) -> None:
        self.id = id
        self.sr = sr
        self.rarity = rarity
        self.parent_id = parent_id
        self.title = title
        self.artist = artist
        self.cumulative_probability = weight
        self.range = R
        self.difficulty_name = diff_name