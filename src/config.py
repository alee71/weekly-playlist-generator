"""Configuration for the weekly playlist generator."""

# Genre preferences - releases matching these will be included
INCLUDE_GENRES = [
    # Punk
    "punk", "hardcore", "post-punk", "post punk", "emo", "ska punk",
    # R&B
    "r&b", "rnb", "soul", "neo-soul", "neo soul",
    # Pop
    "pop", "indie pop", "synth pop", "synthpop", "art pop", "dream pop",
    # Rock
    "rock", "indie rock", "alternative", "garage rock", "psych rock",
    "psychedelic", "shoegaze", "noise rock", "grunge",
    # Metal (no prog)
    "metal", "death metal", "black metal", "doom metal", "thrash",
    "sludge", "stoner metal", "heavy metal", "hardcore",
    # Electronic (underground)
    "electronic", "uk garage", "drum and bass", "dnb", "d&b",
    "jungle", "footwork", "juke", "house", "techno", "ambient",
    "experimental electronic", "idm", "breakbeat", "grime",
    "dubstep",  # real dubstep, not brostep
]

# Releases matching these genres will be excluded
EXCLUDE_GENRES = [
    "prog metal", "progressive metal", "prog rock", "progressive rock",
    "edm", "big room", "festival", "brostep", "mainstream edm",
    "future bass",
]

# Playlist settings
TARGET_PLAYLIST_SIZE = 50
TRACKS_PER_ALBUM_MIN = 3
TRACKS_PER_ALBUM_MAX = 5
RETENTION_WEEKS = 2

# Rate limiting (seconds between requests)
RATE_LIMITS = {
    "bandcamp": 2.0,
    "pitchfork": 5.0,
    "brooklyn_vegan": 2.0,
    "default": 2.0,
}

# User agent for requests
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
