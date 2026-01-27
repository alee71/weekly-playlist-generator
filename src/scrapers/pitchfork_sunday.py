"""Scraper for Pitchfork Sunday Review (classic/older albums)."""

import re
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup

from ..models import ScrapedRelease
from .base import BaseScraper


class PitchforkSundayScraper(BaseScraper):
    """Scraper for Pitchfork Sunday Review - retrospective classic albums."""

    SOURCE_NAME = "Pitchfork Sunday Review"
    BASE_URL = "https://pitchfork.com/reviews/albums/"
    RATE_LIMIT_KEY = "pitchfork"

    def scrape(self) -> List[ScrapedRelease]:
        """Scrape Sunday Review albums from Pitchfork."""
        releases = []

        # Fetch the main reviews page and look for Sunday Review articles
        soup = self._fetch_page(self.BASE_URL)
        if not soup:
            return releases

        # Find Sunday Review articles
        sunday_articles = self._find_sunday_reviews(soup)

        for article in sunday_articles[:5]:  # Limit to recent
            release = self._parse_review_article(article)
            if release:
                releases.append(release)

        self._validate_results(releases)
        return releases

    def _find_sunday_reviews(self, soup: BeautifulSoup) -> List:
        """Find Sunday Review articles on the page."""
        articles = []

        # Look for articles with "Sunday Review" label or tag
        all_articles = soup.select("article, div[class*='review'], a[href*='/reviews/albums/']")

        for article in all_articles:
            article_text = article.get_text().lower()
            # Check if it's labeled as Sunday Review
            if "sunday review" in article_text:
                articles.append(article)
            # Also check for retrospective indicators
            elif any(
                indicator in article_text
                for indicator in ["retrospective", "reissue", "classic"]
            ):
                articles.append(article)

        # If no labeled articles found, try searching the page differently
        if not articles:
            # Look for explicit Sunday Review section
            sunday_section = soup.select_one(
                "[class*='sunday'], [class*='Sunday'], section:has(h2:contains('Sunday'))"
            )
            if sunday_section:
                articles = sunday_section.select("a[href*='/reviews/albums/']")

        return articles

    def _parse_review_article(self, article) -> Optional[ScrapedRelease]:
        """Parse a Sunday Review article for album info."""
        try:
            artist = None
            album = None
            review_url = None
            genres = []

            # Get the review URL
            link = article if article.name == "a" else article.select_one("a[href*='/reviews/albums/']")
            if link:
                review_url = link.get("href", "")
                if not review_url.startswith("http"):
                    review_url = f"https://pitchfork.com{review_url}"

            # Try to get artist/album from article structure
            artist_elem = article.select_one(
                "[class*='artist'], [class*='Artist'], h3"
            )
            album_elem = article.select_one(
                "[class*='album'], [class*='Album'], h4, em, i"
            )

            if artist_elem:
                artist = artist_elem.get_text(strip=True)
            if album_elem:
                album = album_elem.get_text(strip=True)

            # Try to parse from URL if needed
            if review_url and (not artist or not album):
                url_match = re.search(r"/reviews/albums/([^/]+)/", review_url)
                if url_match:
                    slug = url_match.group(1)
                    # Slug format is usually: artist-name-album-name
                    slug_parts = slug.replace("-", " ").title()
                    if not artist:
                        artist = slug_parts
                    if not album:
                        album = slug_parts

            # Get full details from review page
            if review_url:
                page_data = self._parse_full_review_page(review_url)
                if page_data:
                    artist = page_data.get("artist") or artist
                    album = page_data.get("album") or album
                    genres = page_data.get("genres", [])

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
            self.logger.debug(f"Failed to parse Sunday Review article: {e}")

        return None

    def _parse_full_review_page(self, url: str) -> Optional[dict]:
        """Parse full album review page for detailed info."""
        soup = self._fetch_page(url)
        if not soup:
            return None

        data = {}

        # Get artist and album from structured elements
        artist_elem = soup.select_one(
            "h1[class*='artist'], [class*='ArtistName'], [data-testid='artist']"
        )
        album_elem = soup.select_one(
            "h1[class*='album'], [class*='AlbumName'], [data-testid='album']"
        )

        if artist_elem:
            data["artist"] = artist_elem.get_text(strip=True)
        if album_elem:
            data["album"] = album_elem.get_text(strip=True)

        # Get genres
        genres = []
        genre_elems = soup.select(
            "[class*='genre'], [class*='Genre'], a[href*='/genre/']"
        )
        for elem in genre_elems:
            genre = elem.get_text(strip=True).lower()
            if genre and len(genre) < 30:
                genres.append(genre)
        data["genres"] = self._normalize_genres(genres)

        return data
