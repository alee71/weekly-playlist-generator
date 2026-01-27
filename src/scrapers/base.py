"""Base scraper class with common functionality."""

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from ..config import RATE_LIMITS, USER_AGENT
from ..models import ScrapedRelease


class ScraperError(Exception):
    """Base exception for scraper errors."""

    pass


class StructureChangedError(ScraperError):
    """Raised when expected HTML structure is not found."""

    pass


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    SOURCE_NAME: str = ""
    BASE_URL: str = ""
    RATE_LIMIT_KEY: str = "default"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.logger = logging.getLogger(self.__class__.__name__)
        self._last_request_time = 0

    @abstractmethod
    def scrape(self) -> List[ScrapedRelease]:
        """Scrape releases from the source. Must be implemented by subclasses."""
        pass

    def _get_rate_limit(self) -> float:
        """Get rate limit for this scraper."""
        return RATE_LIMITS.get(self.RATE_LIMIT_KEY, RATE_LIMITS["default"])

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        delay = self._get_rate_limit()
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request_time = time.time()

    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page with rate limiting."""
        self._rate_limit()
        try:
            self.logger.debug(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None

    def _safe_extract_text(
        self, element, selector: str, default: str = ""
    ) -> str:
        """Safely extract text from an element using CSS selector."""
        if element is None:
            return default
        try:
            found = element.select_one(selector)
            if found:
                return found.get_text(strip=True)
        except Exception:
            pass
        return default

    def _safe_extract_attr(
        self, element, selector: str, attr: str, default: str = ""
    ) -> str:
        """Safely extract attribute from an element using CSS selector."""
        if element is None:
            return default
        try:
            found = element.select_one(selector)
            if found and found.has_attr(attr):
                return found[attr]
        except Exception:
            pass
        return default

    def _normalize_genres(self, genres: List[str]) -> List[str]:
        """Normalize genre strings for consistent matching."""
        normalized = []
        for genre in genres:
            g = genre.lower().strip()
            # Remove common prefixes/suffixes
            g = g.replace("-", " ").replace("_", " ")
            if g:
                normalized.append(g)
        return list(set(normalized))

    def _validate_results(self, results: List[ScrapedRelease]) -> bool:
        """Validate that scrape returned expected data."""
        if not results:
            self.logger.warning(
                f"{self.SOURCE_NAME}: No results found - site structure may have changed"
            )
            return False
        return True
