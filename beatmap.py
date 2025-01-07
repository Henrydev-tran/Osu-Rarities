from raritycalculation import Calculate_Rarity

class Beatmap:
    def __init__(self, id, title, artist, difficulties, mapper, status) -> None:
        self.id = id
        self.title = title
        self.artist = artist
        self.difficulties = difficulties
        self.mapper = mapper
        self.status = status
        
class Beatmap_Difficulty:
    def __init__(self, sr, parent_id, id, title, artist, diff_name) -> None:
        self.id = id
        self.sr = sr
        self.rarity = Calculate_Rarity(self.sr)
        self.parent_id = parent_id
        self.title = title
        self.artist = artist
        self.difficulty_name = diff_name
        
class Beatmap_Difficulty_Normalized_Range:
    def __init__(self, sr, parent_id, id, title, artist, Nmz_p, R, rarity, diff_name) -> None:
        self.id = id
        self.sr = sr
        self.rarity = rarity
        self.parent_id = parent_id
        self.title = title
        self.artist = artist
        self.normalized_probability = Nmz_p
        self.range = R
        self.difficulty_name = diff_name