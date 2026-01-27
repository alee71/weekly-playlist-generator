"""Scraper for Pitchfork Best New Albums."""

import re
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup

from ..models import ScrapedRelease
from .base import BaseScraper


class PitchforkAlbumsScraper(BaseScraper):
    """Scraper for Pitchfork Best New Albums section."""

    SOURCE_NAME = "Pitchfork Best New Albums"
    BASE_URL = "https://pitchfork.com/reviews/best/albums/"
    RATE_LIMIT_KEY = "pitchfork"

    def scrape(self) -> List[ScrapedRelease]:
        """Scrape best new albums from Pitchfork."""
        releases = []

        soup = self._fetch_page(self.BASE_URL)
        if not soup:
            return releases

        # Try multiple selector patterns as Pitchfork's structure may vary
        album_items = self._find_album_items(soup)

        for item in album_items[:20]:  # Limit to recent
            release = self._parse_album_item(item)
            if release:
                releases.append(release)

        self._validate_results(releases)
        return releases

    def _find_album_items(self, soup: BeautifulSoup) -> List:
        """Find album items using various selector patterns."""
        # Try different possible structures
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

        # Fallback: look for any links to album reviews
        return soup.select("a[href*='/reviews/albums/']")

    def _parse_album_item(self, item) -> Optional[ScrapedRelease]:
        """Parse an album item from the listing."""
        try:
            # Try to extract artist and album
            artist = None
            album = None
            review_url = None
            genres = []

            # Method 1: Structured data
            artist_elem = item.select_one(
                "[class*='artist'], [class*='Artist'], h3, .info h1"
            )
            album_elem = item.select_one(
                "[class*='album'], [class*='Album'], h4, .info h2"
            )

            if artist_elem:
                artist = artist_elem.get_text(strip=True)
            if album_elem:
                album = album_elem.get_text(strip=True)

            # Method 2: Link with combined text
            if not artist or not album:
                link = item if item.name == "a" else item.select_one("a[href*='/reviews/albums/']")
                if link:
                    review_url = link.get("href", "")
                    if not review_url.startswith("http"):
                        review_url = f"https://pitchfork.com{review_url}"

                    # Try to parse from URL: /reviews/albums/artist-name-album-name/
                    url_match = re.search(r"/reviews/albums/([^/]+)/", review_url)
                    if url_match and not (artist and album):
                        slug = url_match.group(1)
                        # Try to split artist-album from slug
                        parts = slug.replace("-", " ").title()
                        if not artist:
                            artist = parts
                        if not album:
                            album = parts

                    # Also try link text
                    link_text = link.get_text(strip=True)
                    if link_text and " - " in link_text:
                        parts = link_text.split(" - ", 1)
                        artist = parts[0].strip()
                        album = parts[1].strip()
                    elif link_text and not artist:
                        artist = link_text

            # Method 3: Separate spans/divs
            if not artist:
                for selector in ["span:first-child", "div:first-child"]:
                    elem = item.select_one(selector)
                    if elem:
                        text = elem.get_text(strip=True)
                        if text and len(text) < 100:
                            artist = text
                            break

            # Get genres from review page if we have URL
            if review_url and not review_url.startswith("http"):
                review_url = f"https://pitchfork.com{review_url}"

            if review_url:
                genres = self._get_genres_from_review(review_url)

            if artist and album:
                return ScrapedRelease(
                    artist=artist,
                    title=album,
                    source=self.SOURCE_NAME,
                    release_type="album",
                    url=review_url or self.BASE_URL,
                    scraped_date=datetime.now().isoformat(),
                    genres=genres,
                )

        except Exception as e:
            self.logger.debug(f"Failed to parse album item: {e}")

        return None

    def _get_genres_from_review(self, url: str) -> List[str]:
        """Extract genres from an album review page."""
        genres = []

        # Only fetch if we have a valid review URL
        if "/reviews/albums/" not in url:
            return genres

        soup = self._fetch_page(url)
        if not soup:
            return genres

        # Look for genre labels
        genre_elems = soup.select(
            "[class*='genre'], [class*='Genre'], .tag, a[href*='/genre/']"
        )
        for elem in genre_elems:
            genre = elem.get_text(strip=True).lower()
            if genre and len(genre) < 30:
                genres.append(genre)

        return self._normalize_genres(genres)
