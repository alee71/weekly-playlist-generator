"""Base scraper class with common functionality."""

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from ..config import RATE_LIMITS
from ..models import ScrapedRelease


class ScraperError(Exception):
      """Base exception for scraper errors."""
      pass

class BaseScraper(ABC):
      """Abstract base class for all scrapers."""

      SOURCE_NAME: str = ""
      BASE_URL: str = ""
      RATE_LIMIT_KEY: str = "default"

      # Rotate user agents to avoid detection
      USER_AGENTS = [
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0
  Safari/537.36",
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0
  Safari/537.36",
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2
  Safari/605.1.15",
      ]

      def __init__(self):
          self.session = requests.Session()
          self._update_headers()
          self.logger = logging.getLogger(self.__class__.__name__)
          self._last_request_time = 0

      def _update_headers(self):
          """Set realistic browser headers."""
          self.session.headers.update({
              "User-Agent": random.choice(self.USER_AGENTS),
              "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
              "Accept-Language": "en-US,en;q=0.9",
              "Accept-Encoding": "gzip, deflate, br",
              "DNT": "1",
              "Connection": "keep-alive",
              "Upgrade-Insecure-Requests": "1",
              "Sec-Fetch-Dest": "document",
              "Sec-Fetch-Mode": "navigate",
              "Sec-Fetch-Site": "none",
              "Sec-Fetch-User": "?1",
              "Cache-Control": "max-age=0",
          })

      @abstractmethod
      def scrape(self) -> List[ScrapedRelease]:
          """Scrape releases from the source."""
          pass

      def _get_rate_limit(self) -> float:
          """Get rate limit for this scraper."""
          return RATE_LIMITS.get(self.RATE_LIMIT_KEY, RATE_LIMITS["default"])

      def _rate_limit(self):
          """Apply rate limiting with jitter."""
          elapsed = time.time() - self._last_request_time
          delay = self._get_rate_limit() + random.uniform(0.5, 2.0)
          if elapsed < delay:
              time.sleep(delay - elapsed)
          self._last_request_time = time.time()

      def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
          """Fetch and parse a page with rate limiting."""
          self._rate_limit()
          self._update_headers()  # Rotate UA each request

          try:
              self.logger.debug(f"Fetching: {url}")
              response = self.session.get(url, timeout=30)
              response.raise_for_status()
              return BeautifulSoup(response.text, "lxml")
          except requests.RequestException as e:
              self.logger.error(f"Failed to fetch {url}: {e}")
              return None

      def _safe_extract_text(self, element, selector: str, default: str = "") -> str:
          """Safely extract text from an element."""
          if element is None:
              return default
          try:
              found = element.select_one(selector)
              if found:
                  return found.get_text(strip=True)
          except Exception:
              pass
          return default

      def _safe_extract_attr(self, element, selector: str, attr: str, default: str = "") -> str:
          """Safely extract attribute from an element."""
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
          """Normalize genre strings."""
          normalized = []
          for genre in genres:
              g = genre.lower().strip().replace("-", " ").replace("_", " ")
              if g and len(g) < 30:
                  normalized.append(g)
          return list(set(normalized))

      def _validate_results(self, results: List[ScrapedRelease]) -> bool:
          """Validate scrape results."""
          if not results:
              self.logger.warning(f"{self.SOURCE_NAME}: No results found")
              return False
          return True
