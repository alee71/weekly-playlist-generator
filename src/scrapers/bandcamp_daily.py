"""Scraper for Bandcamp Daily."""

import re
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup

from ..models import ScrapedRelease
from .base import BaseScraper


class BandcampDailyScraper(BaseScraper):
    """Scraper for Bandcamp Daily - Album of the Day and Essential Releases."""

    SOURCE_NAME = "Bandcamp Daily"
    BASE_URL = "https://daily.bandcamp.com"
    RATE_LIMIT_KEY = "bandcamp"

    # Sections to scrape
    SECTIONS = [
        "/album-of-the-day",
        "/best-of-2025",
        "/lists",
    ]

    def scrape(self) -> List[ScrapedRelease]:
        """Scrape releases from Bandcamp Daily."""
        releases = []

        # Scrape main page for recent articles
        main_soup = self._fetch_page(self.BASE_URL)
        if main_soup:
            releases.extend(self._parse_main_page(main_soup))

        # Scrape specific sections
        for section in self.SECTIONS:
            url = f"{self.BASE_URL}{section}"
            soup = self._fetch_page(url)
            if soup:
                releases.extend(self._parse_section_page(soup, section))

        self._validate_results(releases)
        return self._dedupe_releases(releases)

    def _parse_main_page(self, soup: BeautifulSoup) -> List[ScrapedRelease]:
        """Parse the main Bandcamp Daily page."""
        releases = []

        # Find article links
        article_links = soup.select("a[href*='/album-of-the-day/'], a[href*='/features/']")

        seen_urls = set()
        for link in article_links[:10]:  # Limit to recent articles
            href = link.get("href", "")
            if not href or href in seen_urls:
                continue
            seen_urls.add(href)

            article_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            article_releases = self._parse_article(article_url)
            releases.extend(article_releases)

        return releases

    def _parse_section_page(
        self, soup: BeautifulSoup, section: str
    ) -> List[ScrapedRelease]:
        """Parse a section listing page."""
        releases = []

        # Find article links in the section
        article_links = soup.select("article a[href], .list-article a[href]")

        seen_urls = set()
        for link in article_links[:8]:  # Limit per section
            href = link.get("href", "")
            if not href or href in seen_urls or "#" in href:
                continue
            seen_urls.add(href)

            article_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            # Only process album/music articles
            if any(
                x in article_url
                for x in ["/album-of-the-day/", "/features/", "/best-of", "/lists/"]
            ):
                article_releases = self._parse_article(article_url)
                releases.extend(article_releases)

        return releases

    def _parse_article(self, url: str) -> List[ScrapedRelease]:
        """Parse an individual Bandcamp Daily article for album/artist info."""
        releases = []
        soup = self._fetch_page(url)
        if not soup:
            return releases

        # Look for Bandcamp embeds/links which contain artist and album info
        bandcamp_links = soup.select("a[href*='bandcamp.com']")

        for link in bandcamp_links:
            href = link.get("href", "")
            # Match album pages: artist.bandcamp.com/album/album-name
            album_match = re.search(
                r"https?://([^.]+)\.bandcamp\.com/album/([^/?]+)", href
            )
            if album_match:
                artist_slug = album_match.group(1)
                album_slug = album_match.group(2)

                # Try to get proper names from link text or nearby elements
                artist, album = self._extract_names_from_context(
                    link, artist_slug, album_slug
                )

                # Extract genres from article content
                genres = self._extract_genres_from_article(soup)

                release = ScrapedRelease(
                    artist=artist,
                    title=album,
                    source=self.SOURCE_NAME,
                    release_type="album",
                    url=href,
                    scraped_date=datetime.now().isoformat(),
                    genres=genres,
                )
                releases.append(release)

        return releases

    def _extract_names_from_context(
        self, link, artist_slug: str, album_slug: str
    ) -> tuple:
        """Extract artist and album names from link context."""
        # Try link text first
        link_text = link.get_text(strip=True)
        if link_text and " - " in link_text:
            parts = link_text.split(" - ", 1)
            return parts[0].strip(), parts[1].strip()

        # Try parent elements for formatted text
        parent = link.parent
        if parent:
            # Look for italic (album) and regular (artist) text patterns
            artist_elem = parent.select_one("strong, b")
            album_elem = parent.select_one("em, i")
            if artist_elem and album_elem:
                return artist_elem.get_text(strip=True), album_elem.get_text(strip=True)

        # Fall back to slugs, cleaned up
        artist = artist_slug.replace("-", " ").title()
        album = album_slug.replace("-", " ").title()
        return artist, album

    def _extract_genres_from_article(self, soup: BeautifulSoup) -> List[str]:
        """Extract genre tags from article content."""
        genres = []

        # Look for genre tags/links
        genre_links = soup.select("a[href*='/genres/'], .tag, .genre")
        for link in genre_links:
            genre = link.get_text(strip=True).lower()
            if genre and len(genre) < 30:
                genres.append(genre)

        # Also check meta tags
        meta_keywords = soup.select_one("meta[name='keywords']")
        if meta_keywords:
            keywords = meta_keywords.get("content", "")
            genres.extend([k.strip().lower() for k in keywords.split(",") if k.strip()])

        return self._normalize_genres(genres)

    def _dedupe_releases(self, releases: List[ScrapedRelease]) -> List[ScrapedRelease]:
        """Remove duplicate releases."""
        seen = set()
        unique = []
        for release in releases:
            key = (release.artist.lower(), release.title.lower())
            if key not in seen:
                seen.add(key)
                unique.append(release)
        return unique
