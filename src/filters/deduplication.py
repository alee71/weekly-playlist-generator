"""Deduplication and prioritization of playlist items."""

import logging
from collections import defaultdict
from typing import Dict, List, Tuple

from ..models import PlaylistItem

logger = logging.getLogger(__name__)


class Deduplicator:
    """Handle duplicate tracks across sources and prioritize multi-source items."""

    def deduplicate(
        self, items: List[PlaylistItem]
    ) -> Tuple[List[PlaylistItem], List[PlaylistItem]]:
        """
        Remove duplicates and identify multi-source tracks.

        Args:
            items: List of all playlist items

        Returns:
            Tuple of (priority_items, unique_items):
            - priority_items: Tracks appearing in multiple sources (sorted by source count)
            - unique_items: Deduplicated list of all tracks
        """
        # Group by Spotify URI
        uri_groups: Dict[str, List[PlaylistItem]] = defaultdict(list)
        for item in items:
            uri_groups[item.spotify_uri].append(item)

        priority_items = []
        unique_items = []

        for uri, group in uri_groups.items():
            # Merge items with same URI
            merged = self._merge_items(group)
            unique_items.append(merged)

            # Track items that appeared in multiple sources
            if len(group) > 1:
                priority_items.append(merged)
                logger.info(
                    f"Multi-source track: {merged.artist} - {merged.track} "
                    f"(sources: {merged.sources})"
                )

        # Sort priority items by number of sources (descending)
        priority_items.sort(key=lambda x: len(x.sources), reverse=True)

        logger.info(
            f"Deduplication: {len(items)} items -> {len(unique_items)} unique, "
            f"{len(priority_items)} multi-source"
        )

        return priority_items, unique_items

    def _merge_items(self, items: List[PlaylistItem]) -> PlaylistItem:
        """Merge duplicate items, combining their sources."""
        if len(items) == 1:
            return items[0]

        # Start with a copy of the first item
        merged = items[0].copy()

        # Combine all sources
        all_sources = set()
        for item in items:
            if isinstance(item.sources, list):
                all_sources.update(item.sources)
            else:
                all_sources.add(item.source)

        merged.sources = sorted(list(all_sources))

        return merged

    def group_by_album(
        self, items: List[PlaylistItem]
    ) -> List[PlaylistItem]:
        """
        Reorder items so tracks from the same album appear together.

        This is called after deduplication to ensure album tracks
        are grouped in the final output.
        """
        # Group by (artist, album)
        album_groups: Dict[Tuple[str, str], List[PlaylistItem]] = defaultdict(list)

        for item in items:
            key = (item.artist.lower(), item.album.lower())
            album_groups[key].append(item)

        # Flatten back to list, keeping album tracks together
        # Order albums by their first appearance in the original list
        album_order = []
        seen_albums = set()
        for item in items:
            key = (item.artist.lower(), item.album.lower())
            if key not in seen_albums:
                seen_albums.add(key)
                album_order.append(key)

        grouped = []
        for key in album_order:
            grouped.extend(album_groups[key])

        return grouped
