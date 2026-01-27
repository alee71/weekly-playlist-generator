"""Genre filtering for scraped releases."""

import logging
from typing import List

from ..config import EXCLUDE_GENRES, INCLUDE_GENRES
from ..models import ScrapedRelease

logger = logging.getLogger(__name__)


class GenreFilter:
    """Filter releases based on genre preferences."""

    def __init__(
        self,
        include_genres: List[str] = None,
        exclude_genres: List[str] = None,
    ):
        self.include = [g.lower() for g in (include_genres or INCLUDE_GENRES)]
        self.exclude = [g.lower() for g in (exclude_genres or EXCLUDE_GENRES)]

    def filter(self, releases: List[ScrapedRelease]) -> List[ScrapedRelease]:
        """Filter releases by genre preferences."""
        filtered = []
        for release in releases:
            if self._should_include(release):
                filtered.append(release)
            else:
                logger.debug(
                    f"Filtered out: {release.artist} - {release.title} "
                    f"(genres: {release.genres})"
                )
        return filtered

    def _should_include(self, release: ScrapedRelease) -> bool:
        """
        Determine if release matches genre criteria.

        Logic:
        1. If any genre matches exclude list -> reject
        2. If any genre matches include list -> accept
        3. If no genres specified -> accept (be permissive for discovery)
        """
        release_genres = [g.lower() for g in release.genres]

        # Check exclusions first (these are hard rejections)
        for genre in release_genres:
            for excluded in self.exclude:
                # Check for substring match in either direction
                if excluded in genre or genre in excluded:
                    logger.debug(
                        f"Excluded '{release.artist} - {release.title}' "
                        f"due to genre '{genre}' matching exclude '{excluded}'"
                    )
                    return False

        # If no genres tagged, be permissive (trust the source's curation)
        if not release_genres:
            return True

        # Check inclusions
        for genre in release_genres:
            for included in self.include:
                if included in genre or genre in included:
                    return True

        # No match found - if we have genres but none match our includes,
        # we might be missing something. Be permissive.
        # Only reject if we have strong genre info that doesn't match.
        if len(release_genres) >= 3:
            # Multiple genre tags but none match our preferences
            return False

        # Few or no genre tags - accept to avoid missing good music
        return True
