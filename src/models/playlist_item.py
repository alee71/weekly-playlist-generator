"""Data model for playlist items."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PlaylistItem:
    """Represents a track in the playlist with Spotify info."""

    artist: str
    track: str
    album: str
    spotify_uri: str
    source: str
    scraped_date: str
    sources: List[str] = field(default_factory=list)
    weeks_in_playlist: int = 0

    def __post_init__(self):
        if not self.sources:
            self.sources = [self.source]

    def __hash__(self):
        return hash(self.spotify_uri)

    def __eq__(self, other):
        if not isinstance(other, PlaylistItem):
            return False
        return self.spotify_uri == other.spotify_uri

    def copy(self) -> "PlaylistItem":
        """Create a copy of this item."""
        return PlaylistItem(
            artist=self.artist,
            track=self.track,
            album=self.album,
            spotify_uri=self.spotify_uri,
            source=self.source,
            scraped_date=self.scraped_date,
            sources=self.sources.copy(),
            weeks_in_playlist=self.weeks_in_playlist,
        )
