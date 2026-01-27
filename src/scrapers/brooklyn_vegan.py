"""Scraper for Brooklyn Vegan Notable Releases."""

import re
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup

from ..models import ScrapedRelease
from .base import BaseScraper


class BrooklynVeganScraper(BaseScraper):
    """Scraper for Brooklyn Vegan Notable Releases of the Week."""

    SOURCE_NAME = "Brooklyn Vegan"
    BASE_URL = "https://www.brooklynvegan.com/category/music/new-releases/"
    RATE_LIMIT_KEY = "brooklyn_vegan"

    def scrape(self) -> List[ScrapedRelease]:
        """Scrape notable releases from Brooklyn Vegan."""
        releases = []

        # Fetch the new releases category page
        soup = self._fetch_page(self.BASE_URL)
        if not soup:
            return releases

        # Find the most recent Notable Releases article
        notable_url = self._find_notable_releases_article(soup)
        if notable_url:
            article_soup = self._fetch_page(notable_url)
            if article_soup:
                releases.extend(self._parse_notable_releases_article(article_soup, notable_url))

        # Also try the Indie Basement column
        indie_url = self._find_indie_basement_article(soup)
        if indie_url:
            indie_soup = self._fetch_page(indie_url)
            if indie_soup:
                releases.extend(self._parse_notable_releases_article(indie_soup, indie_url))

        self._validate_results(releases)
        return self._dedupe_releases(releases)

    def _find_notable_releases_article(self, soup: BeautifulSoup) -> Optional[str]:
        """Find the most recent Notable Releases article URL."""
        # Look for article links containing "notable-releases"
        links = soup.select("a[href*='notable-releases'], a[href*='new-releases']")

        for link in links:
            href = link.get("href", "")
            if "notable-releases" in href.lower():
                return href if href.startswith("http") else f"https://www.brooklynvegan.com{href}"

        # Alternative: look in article titles
        articles = soup.select("article, .post, div[class*='post']")
        for article in articles:
            title = article.get_text().lower()
            if "notable releases" in title:
                link = article.select_one("a[href]")
                if link:
                    href = link.get("href", "")
                    return href if href.startswith("http") else f"https://www.brooklynvegan.com{href}"

        return None

    def _find_indie_basement_article(self, soup: BeautifulSoup) -> Optional[str]:
        """Find the most recent Indie Basement article URL."""
        links = soup.select("a[href*='indie-basement'], a[href*='bills-indie-basement']")

        for link in links:
            href = link.get("href", "")
            return href if href.startswith("http") else f"https://www.brooklynvegan.com{href}"

        return None

    def _parse_notable_releases_article(
        self, soup: BeautifulSoup, article_url: str
    ) -> List[ScrapedRelease]:
        """Parse a Notable Releases article for album mentions."""
        releases = []

        # Get the article content
        content = soup.select_one(
            "article .entry-content, .post-content, article .content, main article"
        )
        if not content:
            content = soup.select_one("article") or soup

        # Look for album entries - typically formatted as headers or bold text
        # Pattern 1: h2/h3/h4 headers with "Artist - Album" format
        headers = content.select("h2, h3, h4, strong, b")

        for header in headers:
            text = header.get_text(strip=True)
            release = self._parse_release_text(text, article_url)
            if release:
                # Try to extract genres from surrounding text
                next_elem = header.find_next_sibling()
                if next_elem:
                    release.genres = self._extract_genres_from_text(
                        next_elem.get_text()
                    )
                releases.append(release)

        # Pattern 2: Links with italic album titles
        album_links = content.select("p > strong > a, p > b > a, h2 > a, h3 > a")
        for link in album_links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            # Check parent for full "Artist - Album" pattern
            parent_text = link.parent.get_text(strip=True) if link.parent else text

            release = self._parse_release_text(parent_text, href or article_url)
            if release and release not in releases:
                releases.append(release)

        # Pattern 3: Spotify/Bandcamp embeds
        embed_releases = self._parse_embeds(content)
        for release in embed_releases:
            if release not in releases:
                releases.append(release)

        return releases

    def _parse_release_text(self, text: str, url: str) -> Optional[ScrapedRelease]:
        """Parse artist/album from text like 'Artist - Album' or 'Artist: Album'."""
        if not text or len(text) > 200:
            return None

        # Clean up text
        text = text.strip()

        # Try different separators
        for sep in [" - ", " – ", " — ", ": ", " / "]:
            if sep in text:
                parts = text.split(sep, 1)
                if len(parts) == 2:
                    artist = parts[0].strip()
                    album = parts[1].strip()

                    # Clean up common artifacts
                    album = re.sub(r"\s*\([^)]*\)\s*$", "", album)  # Remove trailing (...)
                    album = album.strip('"\'""''')

                    if artist and album and len(artist) < 100 and len(album) < 100:
                        return ScrapedRelease(
                            artist=artist,
                            title=album,
                            source=self.SOURCE_NAME,
                            release_type="album",
                            url=url,
                            scraped_date=datetime.now().isoformat(),
                            genres=[],
                        )

        return None

    def _parse_embeds(self, content) -> List[ScrapedRelease]:
        """Extract releases from embedded players."""
        releases = []

        # Spotify embeds
        spotify_embeds = content.select(
            "iframe[src*='spotify.com'], a[href*='open.spotify.com']"
        )
        for embed in spotify_embeds:
            src = embed.get("src", "") or embed.get("href", "")
            # Try to extract album/track info from Spotify URL
            match = re.search(r"spotify\.com/(album|track)/([a-zA-Z0-9]+)", src)
            if match:
                # We'll get the actual details from Spotify later
                # Just note that there's a Spotify reference here
                pass

        # Bandcamp embeds
        bandcamp_embeds = content.select(
            "iframe[src*='bandcamp.com'], a[href*='bandcamp.com/album']"
        )
        for embed in bandcamp_embeds:
            src = embed.get("src", "") or embed.get("href", "")
            match = re.search(r"https?://([^.]+)\.bandcamp\.com/album/([^/?]+)", src)
            if match:
                artist = match.group(1).replace("-", " ").title()
                album = match.group(2).replace("-", " ").title()
                releases.append(
                    ScrapedRelease(
                        artist=artist,
                        title=album,
                        source=self.SOURCE_NAME,
                        release_type="album",
                        url=src,
                        scraped_date=datetime.now().isoformat(),
                        genres=[],
                    )
                )

        return releases

    def _extract_genres_from_text(self, text: str) -> List[str]:
        """Extract genre mentions from descriptive text."""
        genres = []
        text_lower = text.lower()

        # Common genre keywords
        genre_keywords = [
            "punk", "hardcore", "post-punk", "emo",
            "rock", "indie", "alternative", "garage",
            "metal", "doom", "black metal", "death metal",
            "electronic", "synth", "ambient",
            "pop", "dream pop", "shoegaze",
            "r&b", "soul", "hip-hop", "rap",
            "folk", "country", "jazz",
        ]

        for keyword in genre_keywords:
            if keyword in text_lower:
                genres.append(keyword)

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
