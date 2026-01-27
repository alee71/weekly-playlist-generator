"""Data model for scraped releases."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ScrapedRelease:
    """Represents a music release scraped from a source."""

    artist: str
    title: str
    source: str
    release_type: str  # 'album' or 'track'
    url: str
    scraped_date: str
    genres: List[str] = field(default_factory=list)
    location: Optional[str] = None

    def __hash__(self):
        return hash((self.artist.lower(), self.title.lower()))

    def __eq__(self, other):
        if not isinstance(other, ScrapedRelease):
            return False
        return (
            self.artist.lower() == other.artist.lower()
            and self.title.lower() == other.title.lower()
        )
