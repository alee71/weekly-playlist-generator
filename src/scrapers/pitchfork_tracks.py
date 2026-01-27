"""Scraper for Pitchfork Best New Tracks."""

import re
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup

from ..models import ScrapedRelease
from .base import BaseScraper


class PitchforkTracksScraper(BaseScraper):
    """Scraper for Pitchfork Best New Tracks section."""

    SOURCE_NAME = "Pitchfork Best New Tracks"
    BASE_URL = "https://pitchfork.com/reviews/best/tracks/"
    RATE_LIMIT_KEY = "pitchfork"

    def scrape(self) -> List[ScrapedRelease]:
        """Scrape best new tracks from Pitchfork."""
        releases = []

        soup = self._fetch_page(self.BASE_URL)
        if not soup:
            return releases

        # Find track items
        track_items = self._find_track_items(soup)

        for item in track_items[:25]:  # Limit to recent
            release = self._parse_track_item(item)
            if release:
                releases.append(release)

        self._validate_results(releases)
        return releases

    def _find_track_items(self, soup: BeautifulSoup) -> List:
        """Find track items using various selector patterns."""
        selectors = [
            "div[class*='review-collection'] > div",
            "ul[class*='object-grid'] li",
            "div[class*='SummaryItem']",
            "article[class*='review']",
            ".review-item",
        ]

        for selector in selectors:
            items = soup.select(selector)
            if items:
                self.logger.debug(f"Found {len(items)} items with selector: {selector}")
                return items

        # Fallback: look for any links to track reviews
        return soup.select("a[href*='/reviews/tracks/']")

    def _parse_track_item(self, item) -> Optional[ScrapedRelease]:
        """Parse a track item from the listing."""
        try:
            artist = None
            track = None
            review_url = None
            genres = []

            # Try to extract artist and track title
            artist_elem = item.select_one(
                "[class*='artist'], [class*='Artist'], h3"
            )
            track_elem = item.select_one(
                "[class*='title'], [class*='Title'], [class*='track'], h4"
            )

            if artist_elem:
                artist = artist_elem.get_text(strip=True)
            if track_elem:
                track = track_elem.get_text(strip=True)
                # Remove quotes if present
                track = track.strip('"\'""''')

            # Try link parsing
            if not artist or not track:
                link = item if item.name == "a" else item.select_one("a[href*='/reviews/tracks/']")
                if link:
                    review_url = link.get("href", "")
                    if not review_url.startswith("http"):
                        review_url = f"https://pitchfork.com{review_url}"

                    link_text = link.get_text(strip=True)

                    # Common format: "Artist: Track Title" or "Artist - Track"
                    for sep in [":", " - ", " – "]:
                        if sep in link_text:
                            parts = link_text.split(sep, 1)
                            artist = artist or parts[0].strip()
                            track = track or parts[1].strip().strip('"\'""''')
                            break

            # Clean up track name
            if track:
                track = track.strip('"\'""''')

            if review_url:
                genres = self._get_genres_from_review(review_url)

            if artist and track:
                return ScrapedRelease(
                    artist=artist,
                    title=track,
                    source=self.SOURCE_NAME,
                    release_type="track",
                    url=review_url or self.BASE_URL,
                    scraped_date=datetime.now().isoformat(),
                    genres=genres,
                )

        except Exception as e:
            self.logger.debug(f"Failed to parse track item: {e}")

        return None

    def _get_genres_from_review(self, url: str) -> List[str]:
        """Extract genres from a track review page."""
        genres = []

        if "/reviews/tracks/" not in url:
            return genres

        soup = self._fetch_page(url)
        if not soup:
            return genres

        genre_elems = soup.select(
            "[class*='genre'], [class*='Genre'], .tag, a[href*='/genre/']"
        )
        for elem in genre_elems:
            genre = elem.get_text(strip=True).lower()
            if genre and len(genre) < 30:
                genres.append(genre)

        return self._normalize_genres(genres)
