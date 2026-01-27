"""Match scraped releases to Spotify tracks."""

import logging
import random
import re
from typing import List, Optional, Tuple

from ..config import TRACKS_PER_ALBUM_MAX, TRACKS_PER_ALBUM_MIN
from ..models import PlaylistItem, ScrapedRelease

logger = logging.getLogger(__name__)


class SpotifyMatcher:
    """
    Match scraped releases to Spotify tracks.

    Uses spotDL library for searching Spotify without requiring API credentials.
    Falls back to basic search if spotDL is not available.
    """

    def __init__(self):
        self._spotdl_available = False
        self._init_spotdl()

    def _init_spotdl(self):
        """Initialize spotDL client if available."""
        try:
            from spotdl import Spotdl
            from spotdl.utils.config import get_config

            # Initialize with default config
            self._spotdl = Spotdl(client_id="", client_secret="")
            self._spotdl_available = True
            logger.info("spotDL initialized successfully")
        except ImportError:
            logger.warning("spotDL not available, will use fallback search")
            self._spotdl_available = False
        except Exception as e:
            logger.warning(f"Failed to initialize spotDL: {e}")
            self._spotdl_available = False

    def match_release(self, release: ScrapedRelease) -> List[PlaylistItem]:
        """
        Match a release to Spotify tracks.

        For albums: Returns 3-5 tracks
        For tracks: Returns single track
        """
        if release.release_type == "track":
            return self._match_track(release)
        else:
            return self._match_album(release)

    def _match_track(self, release: ScrapedRelease) -> List[PlaylistItem]:
        """Match a single track to Spotify."""
        search_query = f"{release.artist} - {release.title}"

        if self._spotdl_available:
            result = self._search_with_spotdl(search_query, limit=1)
            if result:
                return [
                    PlaylistItem(
                        artist=result["artist"],
                        track=result["name"],
                        album=result.get("album", ""),
                        spotify_uri=result["uri"],
                        source=release.source,
                        scraped_date=release.scraped_date,
                    )
                ]

        # Fallback: return a placeholder that user can search manually
        return self._create_manual_search_item(release)

    def _match_album(self, release: ScrapedRelease) -> List[PlaylistItem]:
        """
        Match an album and return 3-5 representative tracks.

        Groups tracks together from the same album.
        """
        items = []
        search_query = f"{release.artist} - {release.title}"

        if self._spotdl_available:
            # Search for album tracks
            results = self._search_album_with_spotdl(release.artist, release.title)
            if results:
                # Select 3-5 tracks
                selected = self._select_album_tracks(results)
                for track in selected:
                    items.append(
                        PlaylistItem(
                            artist=track["artist"],
                            track=track["name"],
                            album=track.get("album", release.title),
                            spotify_uri=track["uri"],
                            source=release.source,
                            scraped_date=release.scraped_date,
                        )
                    )
                return items

        # Fallback
        return self._create_manual_search_item(release)

    def _search_with_spotdl(
        self, query: str, limit: int = 1
    ) -> Optional[dict]:
        """Search Spotify using spotDL."""
        try:
            from spotdl.types.song import Song

            songs = Song.from_search_term(query)
            if songs:
                song = songs if not isinstance(songs, list) else songs[0]
                return {
                    "name": song.name,
                    "artist": song.artist,
                    "album": song.album_name,
                    "uri": f"spotify:track:{song.song_id}",
                    "duration": song.duration,
                }
        except Exception as e:
            logger.debug(f"spotDL search failed for '{query}': {e}")
        return None

    def _search_album_with_spotdl(
        self, artist: str, album: str
    ) -> List[dict]:
        """Search for album tracks using spotDL."""
        tracks = []
        try:
            from spotdl.types.song import Song

            # Try searching for the album
            query = f"{artist} - {album}"
            results = Song.list_from_search_term(query)

            if results:
                # Filter to tracks from the same album
                for song in results:
                    if self._is_same_album(song, artist, album):
                        tracks.append({
                            "name": song.name,
                            "artist": song.artist,
                            "album": song.album_name,
                            "uri": f"spotify:track:{song.song_id}",
                            "duration": song.duration,
                        })

        except Exception as e:
            logger.debug(f"spotDL album search failed for '{artist} - {album}': {e}")

        return tracks

    def _is_same_album(self, song, artist: str, album: str) -> bool:
        """Check if a song belongs to the target album."""
        # Normalize for comparison
        def normalize(s):
            return re.sub(r"[^\w\s]", "", s.lower())

        song_album = normalize(song.album_name) if song.album_name else ""
        song_artist = normalize(song.artist) if song.artist else ""
        target_album = normalize(album)
        target_artist = normalize(artist)

        # Check album name similarity
        album_match = (
            target_album in song_album
            or song_album in target_album
            or self._fuzzy_match(target_album, song_album)
        )

        # Check artist similarity
        artist_match = (
            target_artist in song_artist
            or song_artist in target_artist
            or self._fuzzy_match(target_artist, song_artist)
        )

        return album_match and artist_match

    def _fuzzy_match(self, s1: str, s2: str, threshold: float = 0.7) -> bool:
        """Simple fuzzy string matching."""
        if not s1 or not s2:
            return False

        # Simple Jaccard similarity on words
        words1 = set(s1.split())
        words2 = set(s2.split())

        if not words1 or not words2:
            return False

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return (intersection / union) >= threshold

    def _select_album_tracks(self, tracks: List[dict]) -> List[dict]:
        """
        Select 3-5 representative tracks from an album.

        Filters out very short/long tracks and spreads selection.
        """
        if len(tracks) <= TRACKS_PER_ALBUM_MAX:
            return tracks

        # Filter by duration (90 seconds to 10 minutes)
        filtered = [
            t for t in tracks
            if 90 <= (t.get("duration", 180) or 180) <= 600
        ]

        if len(filtered) < TRACKS_PER_ALBUM_MIN:
            filtered = tracks

        # Select tracks spread across the album
        num_tracks = random.randint(
            TRACKS_PER_ALBUM_MIN,
            min(TRACKS_PER_ALBUM_MAX, len(filtered))
        )

        if len(filtered) <= num_tracks:
            return filtered

        # Try to get a spread of tracks rather than just the first few
        step = len(filtered) // num_tracks
        selected = []
        for i in range(num_tracks):
            idx = min(i * step, len(filtered) - 1)
            if filtered[idx] not in selected:
                selected.append(filtered[idx])

        return selected

    def _create_manual_search_item(
        self, release: ScrapedRelease
    ) -> List[PlaylistItem]:
        """
        Create placeholder item for manual search.

        When automatic matching fails, we still want to include
        the release in the output so the user can search manually.
        """
        # Create a search URI that will open Spotify search
        search_term = f"{release.artist} {release.title}".replace(" ", "%20")
        search_uri = f"spotify:search:{search_term}"

        return [
            PlaylistItem(
                artist=release.artist,
                track=release.title if release.release_type == "track" else f"[Album: {release.title}]",
                album=release.title if release.release_type == "album" else "",
                spotify_uri=search_uri,
                source=release.source,
                scraped_date=release.scraped_date,
            )
        ]
