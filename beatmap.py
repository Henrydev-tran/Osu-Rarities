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
    def __init__(self, sr, parent_id, id, title, artist) -> None:
        self.id = id
        self.sr = sr
        self.rarity = Calculate_Rarity(self.sr)
        self.parent_id = parent_id
        self.title = title
        self.artist = artist