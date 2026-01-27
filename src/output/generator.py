"""Output generation for playlist files."""

import logging
from datetime import datetime
from pathlib import Path
from typing import List

from ..models import PlaylistItem

logger = logging.getLogger(__name__)


class OutputGenerator:
    """Generate human-readable and machine-readable playlist output."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        items: List[PlaylistItem],
        priority_items: List[PlaylistItem],
    ) -> Path:
        """
        Generate playlist output file.

        Format:
        1. Header with date and stats
        2. Priority section (multi-source tracks)
        3. Full playlist grouped by album (artist - track - source)
        4. Spotify URIs section (for copy/paste)

        Args:
            items: All playlist items (already grouped by album)
            priority_items: Tracks that appeared in multiple sources

        Returns:
            Path to the generated output file
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_file = self.output_dir / f"playlist_{date_str}.txt"

        lines = []

        # Header
        lines.append(f"Weekly Playlist - {date_str}")
        lines.append(f"Total tracks: {len(items)}")
        lines.append(f"Priority tracks (multiple sources): {len(priority_items)}")
        lines.append("=" * 70)
        lines.append("")

        # Priority section
        if priority_items:
            lines.append("=== PRIORITY TRACKS (Recommended by Multiple Sources) ===")
            lines.append("")
            for item in priority_items:
                sources = ", ".join(item.sources)
                lines.append(f"  * {item.artist} - {item.track}")
                if item.album:
                    lines.append(f"    Album: {item.album}")
                lines.append(f"    Sources: {sources}")
                lines.append("")
            lines.append("=" * 70)
            lines.append("")

        # Full playlist grouped by album
        lines.append("=== FULL PLAYLIST ===")
        lines.append("(Tracks from the same album are grouped together)")
        lines.append("")

        current_album = None
        track_num = 1

        for item in items:
            album_key = (item.artist.lower(), item.album.lower()) if item.album else None

            # Print album header when album changes
            if album_key and album_key != current_album:
                if current_album is not None:
                    lines.append("")  # Blank line between albums
                lines.append(f"  [{item.artist} - {item.album}]")
                current_album = album_key
            elif not album_key and current_album is not None:
                lines.append("")
                current_album = None

            # Track line
            source = item.sources[0] if item.sources else item.source
            week_info = ""
            if item.weeks_in_playlist > 0:
                week_info = f" (week {item.weeks_in_playlist + 1})"

            if item.album:
                lines.append(f"    {track_num:3}. {item.track}{week_info}")
            else:
                lines.append(
                    f"  {track_num:3}. {item.artist} - {item.track}{week_info}"
                )
                lines.append(f"       Source: {source}")

            track_num += 1

        lines.append("")

        # Spotify URIs section
        lines.append("=" * 70)
        lines.append("=== SPOTIFY URIs ===")
        lines.append("Copy all URIs below and paste into Spotify desktop app:")
        lines.append("")
        lines.append("Instructions:")
        lines.append("1. Open Spotify desktop app")
        lines.append("2. Create a new playlist or open your existing weekly playlist")
        lines.append("3. Select and copy all URIs below (Ctrl+A, Ctrl+C)")
        lines.append("4. Click inside the playlist and paste (Ctrl+V)")
        lines.append("")
        lines.append("--- START URIS ---")

        # Separate valid URIs from search URIs
        valid_uris = []
        search_uris = []

        for item in items:
            if item.spotify_uri.startswith("spotify:track:"):
                valid_uris.append(item.spotify_uri)
            elif item.spotify_uri.startswith("spotify:search:"):
                search_uris.append((item.artist, item.track, item.spotify_uri))

        for uri in valid_uris:
            lines.append(uri)

        lines.append("--- END URIS ---")

        # Manual search section if needed
        if search_uris:
            lines.append("")
            lines.append("=" * 70)
            lines.append("=== MANUAL SEARCH NEEDED ===")
            lines.append("These tracks couldn't be automatically matched.")
            lines.append("Search for them manually in Spotify:")
            lines.append("")
            for artist, track, _ in search_uris:
                lines.append(f"  - {artist} - {track}")

        # Write file
        content = "\n".join(lines)
        output_file.write_text(content, encoding="utf-8")

        logger.info(f"Output written to: {output_file}")
        logger.info(f"  - {len(valid_uris)} Spotify URIs")
        logger.info(f"  - {len(search_uris)} items need manual search")

        return output_file
